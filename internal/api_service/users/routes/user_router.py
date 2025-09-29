from sqlalchemy import text
from main import get_s3
from typing_extensions import Annotated, List
from fastapi import APIRouter, Request, UploadFile, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from botocore.exceptions import BotoCoreError, ClientError
import secrets, base64

from auth.models.token import Token
from auth.services.auth_service import authenticate_user, create_access_token
from db_service.utils.db_utils import get_session
from db_service.models.py_models import *
from db_service.models.models import *
from users.services.stream_service import StreamWrapper


user_router = APIRouter(
  prefix="/user",
  tags=["User"]
)
# @app.get("/dicoms/{aid}", dependencies=[Depends(get_current_active_user)], response_model=List[Record])
@user_router.get("/{aid}/sessions", response_model=List[Record])
async def get_dicoms_by_user(aid: int, session: Depends[get_session]):
  """
  Fetch all 'Accessions' by user
  """
  result = await session.execute(
    text("get_dicoms_by_aid"),
    {"aid_input": aid}
  )
  return [Record(**dict(row)) for row in result.mappings()]


@user_router.get("/{aid}/session", response_model=ReadAccession)
async def get_data_by_session(aid: int, session_id: int, session: Depends[get_session]):
  """
  Fetch all Coned CTs by Accession (currently called 'Dicoms')
  return (most importantly) 
  """
  result = await session.execute(
    text("get_accession"),
    {"aid_input": aid, "dicom_id_input": session_id}
  )
  res = result.mappings().all()
  accession: ReadAccession
  files: List[File]
  last_dicom_name = ""
  for i,row in enumerate(res):
    if i > 0 and last_dicom_name != row["dicom_name"]:
      accession.files = files
      return accession
    accession.created_at = row["created_at"]
    accession.name = row["dicom_name"]
    files.append(
      File(
        filetype=row["filetype"],
        object_key=row["object_key"]
      )
    )
  accession.files = files
  return accession

# make new accession? 
  # upload new dicoms?

def add_record(record, session: AsyncSession) -> int:
  session.add(record)
  session.refresh(record)
  return session.record


@user_router.post("/new_accession")
async def create_accession(accession: WriteAccession, session: Depends[get_session], s3_data: Depends[get_s3], files: List[UploadFile] = File(...)):
  """
  Returns 2 DicomFiles objects:
  {
    "dicom_id": x,
    "stats": {
      "stat_id": z,
      "agaston_score": 5,
    }
    "files": [
      {
        "file_id": y1,
        "filetype: "mask",
        "object_key": "dicoms/accession_id/masks/unique_id.img"
      }
    ]
  }
  """
  # write to S3, get object key  
  client, bucket = s3_data
  accession_id = -1
  try:
    for i, file in enumerate(files):
      # background task? 
      key = f"/Dicoms/{accession.aid}/{datetime.now()}_{file.filename}"
      client.upload_fileobj(file.file, bucket, key)
      
      # add to: FileRecords, Dicoms, Dicomfiles
      file_record = FileRecords(filetype="slice", object_key=key)
      file_record = add_record(file_record)
      if i == 0:
        new_accession = Dicoms(dicom_name=accession.dicom_name)
        new_accession = add_record(new_accession, session)
        accession_id = new_accession.dicom_id
      
      # add to DICOMFiles junction table,
      await session.execute(
        text("""
             INSERT INTO DICOMFILES (DICOM_ID, FILE_ID)
             VALUES (:dicom_id, :file_id)
             """),
        {
          "dicom_id": accession_id,
          "file_id": file_record.file_id
        }
      )
      # then PatientDicoms junction table
      
      patient_dicom_record = PatientDicoms(patient_id=accession.aid, dicom_id=accession_id)
      patient_dicom_record = add_record(patient_dicom_record, session)
      
      # dummy function: ML pipeline generates:
      #   1. Mask
      #   2. Agaston
      # introduce dummy func as celery task?

    return True
      
  except Exception as e:
    session.rollback()
    # send to kafka next time
    raise HTTPException(status_code=501, detail=f"Error occured while file upload: {e}")
  return True


def get_random_str(k=32):
  return base64.urlsafe_b64decode(secrets.token_bytes(k)).rstrip(b'=').decode("utf-8")


@user_router.post("/new_accession/fast")
async def create_accession(accession: WriteAccession, session: Depends[get_session], s3_data: Depends[get_s3], request: Request):
  try:  
    stream_wrapper = StreamWrapper(request.stream())
    random_val = get_random_str()
    key = f"/Dicoms/{accession.aid}_{datetime.now()}_{random_val}"
    client, bucket = s3_data
    client.upload_fileobj(stream_wrapper, bucket, key)
    
    # write to postgres
    
    
    return True
  except (BotoCoreError, ClientError) as e:
    raise HTTPException(status_code=500, detail=str(e))



@user_router.post("/update_accession")
async def update_accession(accession: UpdateAccession):
  return