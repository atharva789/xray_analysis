# Imaging Segmentation Platform

End-to-end FastAPI application for managing cardiac CT accessions, preprocessing uploads, and serving neural-net segmentations through NVIDIA Triton. The code base demonstrates how to combine Python microservices, GPU inference, and AWS-grade infrastructure patterns in a single repo.

## Why It Matters

- **Clinical data ingestion** – Users upload raw DICOM slices through the `internal/frontend_service` PyQt client, the FastAPI backend persists metadata in Postgres and writes the binaries to object storage (AWS S3 in production, configurable locally).
- **Asynchronous ML pipeline** – `celery` + Redis queue drive heavy preprocessing and inference work so API latency never spikes. Tasks normalize/resize medical volumes with OpenCV/pydicom and then call Triton via `tritonclient`.
- **GPU-first serving** – `deploy/compose/docker-compose.yaml` stands up Triton with a TorchScript MONAI UNet (`internal/inference/triton_models/img_seg_model`) so the same model artifact can run locally or on managed GPU fleets (e.g., Amazon ECS/EKS with GPU nodes).
- **Modern backend tooling** – FastAPI + SQLAlchemy + Alembic power the REST surface and migrations (`internal/api_service`). Pydantic models, dependency-injected sessions, and typed routers keep the codebase maintainable.
- **Infrastructure knowledge** – Docker multi-service stack (Postgres, Redis, Triton, FastAPI, Celery) mirrors a realistic AWS deployment pipeline, emphasizing containerization, environment-based configuration, and secret management.

These touchpoints map directly to the skills AWS recruiters screen for in SWE/ML engineer roles: distributed systems, MLOps, inference serving, and cloud-native design.

## Architecture Overview

```
PyQt Client ──▶ FastAPI (internal/api_service)
                 │   └── Uploads metadata to Postgres
                 │   └── Streams raw DICOMs to S3
                 ▼
            Redis + Celery (task_queue)
                 │   └── Downloads S3 objects
                 │   └── Applies MONAI-style preprocessing
                 │   └── Calls Triton via gRPC
                 ▼
            Triton Server (deploy/compose service)
                 │   └── Hosts TorchScript UNet
                 │   └── Returns masks
                 ▼
             S3 + Postgres (results, metadata)
```

## Key Components

| Layer | Highlights |
| ----- | ---------- |
| **FastAPI service** (`internal/api_service`) | Auth, user sessions, `/user/new_accession` uploads, S3 presigned URLs, SQLAlchemy models/migrations, dependency-injected services. |
| **Task queue** (`internal/api_service/task_queue`) | Redis-backed Celery app, preprocessing pipeline using `pydicom`, `opencv-python-headless`, NumPy. Calls Triton via gRPC to obtain segmentation masks. |
| **Inference assets** (`internal/inference`) | MONAI training notebook (`segmentation.ipynb`), TorchScript export (`model.pt`), Triton model repo (`triton_models/img_seg_model`). |
| **Container stack** (`deploy/compose/docker-compose.yaml`) | Postgres 15, Redis 7, Triton 24.04, FastAPI, Celery worker. Exposes ports for API (8010) and Triton (8000/8001/8002). |
| **Desktop viewer** (`internal/frontend_service`) | PyQt GUI for selecting sessions, launching viewers, and performing uploads/downloads. |

## Getting Started

1. **Clone & configure**
   ```bash
   git clone https://github.com/atharva789/xray_analysis.git
   cd xray_analysis
   cp deploy/.env.backend.local.example deploy/.env.backend.local  # set DB, S3, auth secrets
   ```
   Provide AWS credentials (or MinIO equivalents) in your shell so the API and Celery worker can talk to object storage.

2. **Build and run the stack**
   ```bash
   cd deploy/compose
   docker compose up --build
   ```
   This launches Postgres, Redis, Triton, FastAPI, and the Celery worker. Triton automatically loads the TorchScript model from `internal/inference/triton_models`.

3. **Interact**
   - Use the PyQt frontend (`internal/frontend_service`) or call the FastAPI endpoints (`/user/new_accession`, `/user/sessions`) to upload CT series.
   - Celery downloads the raw files from S3, clips/intensity-normalizes, resizes each slice to `96×96`, uploads the processed tensor, and finally invokes Triton for segmentation. The resulting masks are written back next to the accession prefix.
   - Retrieve presigned URLs via `/user/get-session/{id}` to download slices, processed data, or masks.

## Development Notes

- **Training notebook** – `internal/inference/segmentation.ipynb` documents the MONAI UNet setup (2D `spatial_dims`, 1-channel input). The notebook also exports the TorchScript artifact and matching Triton config.
- **Task queue** – `internal/api_service/task_queue/tasks.py` is the best place to extend preprocessing (e.g., additional augmentations, stats) or change Triton model names via environment variables (`TRITON_URL`, `TRITON_MODEL_NAME`, etc.).
- **Database models** – Update `internal/api_service/db_service/models` and run Alembic migrations (`alembic upgrade head`) whenever schema changes are required.
- **Secrets** – `.gitignore` excludes training data, model repos, and `.env*` files. Use AWS Secrets Manager or SSM Parameter Store in production.

## Showcased Skills

- **Cloud-native ML delivery**: storing datasets/masks in S3, orchestrating preprocessing through Celery, and serving inference through Triton positions the project squarely in AWS MLOps territory.
- **Infrastructure as Code**: Docker Compose defines all runtime dependencies, mirroring a multi-container deployment that could be lifted into ECS/EKS easily.
- **Systems design**: decoupled frontend, API, task queue, and inference services highlight asynchronous design patterns, fault tolerance (Celery retries), and horizontal scalability.
- **Medical imaging domain**: handling DICOM metadata, spacing/orientation transforms, and MONAI data loaders show familiarity with healthcare data compliance and preprocessing nuances.

## Next Steps

- Automate model retraining/export pipelines.
- Add observability (Prometheus/Grafana) for queue depth and inference latency.
- Integrate IAM roles / STS tokens for S3 access when deploying to AWS.

For questions or collaboration opportunities, feel free to open an issue or reach out directly. This project reflects hands-on experience with AWS-aligned ML systems, from ingestion to GPU inference. !*** End Patch*** End Patch נה? Error? Need proper apply_patch without escaping? use apply_patch. need info string? Already includes markers. call apply_patch. need no extra characters. Start again properly. Use *** Begin Patch etc. Provide file creation. Let's reapply. Need instructions: not to include ??? ok do. use apply_patch. let's do. 
