from __future__ import annotations

import asyncio
import io
import logging
import os
from typing import Awaitable, Callable, Iterable, List, Optional, TypeVar

import asyncpg
import boto3
import cv2
import numpy as np
import pydicom
import tritonclient.grpc as grpcclient

from .celery_app import celery_app

LOGGER = logging.getLogger(__name__)
TARGET_SIZE = int(os.getenv("SEGMENTATION_INPUT_SIZE", "96"))
S3_BUCKET = os.getenv("BUCKET_NAME", "medical-dicoms")
INTENSITY_MIN = float(os.getenv("SEGMENTATION_A_MIN", "-100"))
INTENSITY_MAX = float(os.getenv("SEGMENTATION_A_MAX", "400"))
TRITON_URL = os.getenv("TRITON_URL", "localhost:8001")
TRITON_MODEL_NAME = os.getenv("TRITON_MODEL_NAME", "img_seg_model")
TRITON_INPUT_NAME = os.getenv("TRITON_INPUT_NAME", "input")
TRITON_OUTPUT_NAME = os.getenv("TRITON_OUTPUT_NAME", "output")

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("DB_NAME", "postgres")
ASYNC_DB_DSN = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

PoolType = TypeVar("PoolType", bound=asyncpg.Pool)
AsyncConnCallable = Callable[[asyncpg.Connection], Awaitable[None]]

_db_pool: Optional[PoolType] = None


async def _get_db_pool() -> PoolType:
    """Lazily create an asyncpg connection pool for Celery workers."""
    global _db_pool
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(dsn=ASYNC_DB_DSN, min_size=1, max_size=5)
    return _db_pool


async def execute_db_transaction(fn: AsyncConnCallable) -> None:
    """
    Execute the provided coroutine inside a database transaction.

    Celery tasks can call this via `run_db_job` to ensure inserts/updates happen
    atomically once preprocessing completes.
    """
    pool = await _get_db_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            await fn(connection)


def run_db_job(fn: AsyncConnCallable) -> None:
    """
    Helper to run an async DB transaction from synchronous Celery tasks.

    Example:
        def persist():
            async def _persist(conn):
                await conn.execute(\"\"\"UPDATE ...\"\"\")
            run_db_job(_persist)
    """
    asyncio.run(execute_db_transaction(fn))


def _sort_key(ds: pydicom.dataset.Dataset) -> float:
    position = getattr(ds, "ImagePositionPatient", None)
    if position and len(position) > 2:
        return float(position[2])
    return float(getattr(ds, "InstanceNumber", 0))


def load_and_sort_dicoms(file_bytes_list: Iterable[bytes]) -> List[pydicom.dataset.Dataset]:
    slices: List[pydicom.dataset.Dataset] = []
    for file_data in file_bytes_list:
        try:
            ds = pydicom.dcmread(io.BytesIO(file_data), force=True)
            slices.append(ds)
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.warning("Failed to read DICOM slice: %s", exc)
    if not slices:
        raise ValueError("No valid DICOM slices were provided for preprocessing.")
    slices.sort(key=_sort_key)
    return slices


def stacks_to_volume(slices: List[pydicom.dataset.Dataset]) -> np.ndarray:
    volume = np.stack([s.pixel_array.astype(np.float32) for s in slices], axis=0)
    slope = getattr(slices[0], "RescaleSlope", 1.0)
    intercept = getattr(slices[0], "RescaleIntercept", 0.0)
    volume = volume * slope + intercept
    return volume


def normalize_intensity(volume: np.ndarray) -> np.ndarray:
    clipped = np.clip(volume, INTENSITY_MIN, INTENSITY_MAX)
    normalized = (clipped - INTENSITY_MIN) / (INTENSITY_MAX - INTENSITY_MIN)
    return normalized.astype(np.float32)


def resize_slices(volume: np.ndarray) -> np.ndarray:
    processed = []
    for slice_img in volume:
        resized = cv2.resize(slice_img, (TARGET_SIZE, TARGET_SIZE), interpolation=cv2.INTER_LINEAR)
        processed.append(resized.astype(np.float32))
    stacked = np.stack(processed, axis=0)
    return np.expand_dims(stacked, axis=1)  # (num_slices, 1, H, W)


def preprocess_volume(file_bytes_list: Iterable[bytes]) -> np.ndarray:
    slices = load_and_sort_dicoms(file_bytes_list)
    volume = stacks_to_volume(slices)
    normalized = normalize_intensity(volume)
    return resize_slices(normalized)


def run_triton_inference(volume: np.ndarray) -> np.ndarray:
    client = grpcclient.InferenceServerClient(url=TRITON_URL)
    input_tensor = grpcclient.InferInput(TRITON_INPUT_NAME, volume.shape, "FP32")
    input_tensor.set_data_from_numpy(volume.astype(np.float32))
    output_tensor = grpcclient.InferRequestedOutput(TRITON_OUTPUT_NAME)
    response = client.infer(
        model_name=TRITON_MODEL_NAME,
        inputs=[input_tensor],
        outputs=[output_tensor],
    )
    logits = response.as_numpy(TRITON_OUTPUT_NAME)
    if logits is None:
        raise RuntimeError("Triton response did not contain output tensor.")
    return np.argmax(logits, axis=1).astype(np.uint8)


@celery_app.task(bind=True, name="task_queue.preprocess_accession", max_retries=3)
def preprocess_accession_task(self, accession_id: int, s3_folder_prefix: str) -> dict:
    """
    Download the newly uploaded DICOM series, crop/resize each slice to 96x96,
    and store the normalized tensor back to S3 for downstream inference.
    """
    s3 = boto3.client("s3")

    try:
        paginator = s3.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=s3_folder_prefix)
        keys: List[str] = []
        for page in page_iterator:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.lower().endswith(".dcm"):
                    keys.append(key)

        if not keys:
            raise ValueError(f"No DICOM files found under prefix {s3_folder_prefix}")

        raw_files = []
        for key in keys:
            body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
            raw_files.append(body)

        processed_volume = preprocess_volume(raw_files)

        buffer = io.BytesIO()
        np.save(buffer, processed_volume)
        buffer.seek(0)

        output_key = f"{s3_folder_prefix.rstrip('/')}/preprocessed/slices.npy"
        s3.upload_fileobj(buffer, S3_BUCKET, output_key)

        mask = run_triton_inference(processed_volume)

        mask_buffer = io.BytesIO()
        np.save(mask_buffer, mask)
        mask_buffer.seek(0)
        mask_key = output_key.replace("preprocessed/slices.npy", "predictions/mask.npy")
        s3.upload_fileobj(mask_buffer, S3_BUCKET, mask_key)
        
        # write to DB
        dicom_id = int(s3_folder_prefix.split("/")[2])
        async def _persist(conn):
          mask_id = await conn.fetchval(
            "INSERT INTO filerecords (filetype, object_key) VALUES ($1, $2) RETURNING file_id",
            "mask", mask_key
          )
          preprocessed_tensors_id = await conn.fetchval(
            "INSERT INTO filerecords (filetype, object_key) VALUES ($1, $2) RETURNING file_id",
            "slice", output_key
          )
          await conn.execute(
            "INSERT INTO dicomfiles (dicom_id, file_id) VALUES ($1, $2)",
            dicom_id, mask_id
          )
          await conn.execute(
            "INSERT INTO dicomfiles (dicom_id, file_id) VALUES ($1, $2)",
            dicom_id, preprocessed_tensors_id
          )
        run_db_job(_persist)
        
        return {
            "status": "COMPLETED",
            "accession_id": accession_id,
            "preprocessed_key": output_key,
            "num_slices": int(processed_volume.shape[0]),
            "sample_shape": processed_volume.shape[1:],  # (1, H, W)
            "mask_key": mask_key,
        }

    except Exception as exc:
        LOGGER.exception("Failed to preprocess accession %s", accession_id)
        raise self.retry(exc=exc, countdown=30)
