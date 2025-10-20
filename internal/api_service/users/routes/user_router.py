from sqlalchemy import text
from cloud_services import get_s3
from typing_extensions import Annotated, List
from fastapi import APIRouter, Form, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from botocore.exceptions import BotoCoreError, ClientError
import secrets, base64

from auth.models.token import Token
from auth.services.auth_service import *
from db_service.utils.db_utils import *
from db_service.models.py_models import *
from db_service.models.models import *
from users.services.stream_service import StreamWrapper

URL_EXPIRATION_TIME=3600

def get_temp_url(client, bucket, key):
  try:
    response = client.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': bucket, 'Key':key},
        ExpiresIn=URL_EXPIRATION_TIME
      )
    return response
  except Exception as e:
    print(f"{e}")

user_router = APIRouter(
  tags=["User"]
)
# @app.get("/dicoms/{aid}", dependencies=[Depends(get_current_active_user)], response_model=List[Record])
@user_router.get("/sessions")
async def get_dicoms_by_user(user = Depends(get_current_active_user), session: tuple = Depends(get_session)) -> List[DBAccession]:
  """
  Fetch all 'Accessions' by user
  """
  aid = user.aid
  result = await session.execute(
    text("select distinct * from get_dicoms_by_aid(:aid_input)").bindparams(aid_input=aid)
  )
  return [
    DBAccession(
      aid=aid,
      dicom_id=row["dicom_id"],
      created_at=row["created_at"],
      agaston_score=row["agaston_score"],
      dicom_name=row["dicom_name"],
    )
    for row in result.mappings()
  ]


@user_router.get("get-session/{session_id}")
async def get_data_by_session(
  aid: int, 
  session_id: int, 
  user = Depends(get_current_active_user),
  session: AsyncSession = Depends(get_session), 
  data: tuple = Depends(get_s3),
  ):
  """
  Fetch all Coned CTs by Accession (currently called 'Dicoms')
  return (most importantly) 
  """
  client, bucket = data
  aid = user.aid
  result = await session.execute(
    text("select * from get_accession(:aid_input,:dicom_id_input)").bindparams(
      aid_input=aid,dicom_id_input=session_id)
  )
  res = result.mappings().all()
  files: List[FileResponse] = []
  created_at = None
  dicom_name = None
  agaston_score = None
  if len(res) == 0:
    return None
  for row in res:    
    created_at = row["created_at"]
    dicom_name = row["dicom_name"]
    agaston_score = row["agaston_score"]
    temp_url = get_temp_url(client,bucket,row["object_key"])
    files.append(
      FileResponse(
        type=row["filetype"],
        object_key=row["object_key"],
        s3_url=temp_url 
      )
    )
  accession = ReadAccession(
    aid=aid,
    created_at=created_at,
    dicom_name=dicom_name,
    dicom_id=session_id,
    agaston_score=agaston_score,
    files=files
  )
  return accession

# make new accession? 
  # upload new dicoms?

async def add_record(record: any, session: AsyncSession) -> int:
  session.add(record)
  await session.flush()
  await session.refresh(record)
  return record


@user_router.post("/new_accession")
async def create_accession(
  files: Annotated[List[UploadFile], File()],
  accession: str = Form(),
  session: AsyncSession = Depends(get_session), 
  s3_data: tuple = Depends(get_s3)):
  """
  Returns 1 DicomFiles object:
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
    accession = WriteAccession.model_validate_json(accession)
    mask_url = ""
    for i, file in enumerate(files):
      # background task? 
      key = f"/Dicoms/{accession.aid}/{datetime.now()}_{file.filename}"
      client.upload_fileobj(file.file, bucket, key)
      
      # get pre-signed URL for DUMMY 
      # AI generated image mask
      mask_url = get_temp_url(client,bucket,key)
      
      # add to: FileRecords, Dicoms, Dicomfiles
      file_record = FileRecords(filetype="slice", object_key=key)
      file_record = await add_record(file_record, session)
      if i == 0:
        new_accession = Dicoms(dicom_name=accession.dicom_name)
        new_accession = await add_record(new_accession, session)
        accession_id = new_accession.dicom_id
      
      # add to DICOMFiles junction table,
      await session.execute(
        text("""
             INSERT INTO DICOMFILES (DICOM_ID, FILE_ID)
             VALUES (:dicom_id, :file_id)
             """).bindparams(
               dicom_id=accession_id,
               file_id=file_record.file_id
             )
      )
      # then PatientDicoms junction table
      
      patient_dicom_record = PatientDicoms(patient_id=accession.aid, dicom_id=accession_id)
      patient_dicom_record = await add_record(patient_dicom_record, session)
      
      # dummy function: ML pipeline generates:
      #   1. Mask
      #   2. Agaston
      # introduce dummy func as celery task?
    annotated_file = UploadNewFile(
      type="mask",
      object_key="",
      s3_url=mask_url
    )
    
    await session.commit()
    
    return WriteAccession(
      aid=accession_id,
      dicom_name=accession.dicom_name,
      agaston_score=0,
      files=[annotated_file]
    )
      
  except Exception as e:
    await session.rollback()
    # send to kafka next time
    raise HTTPException(status_code=501, detail=f"Error occured while file upload: {e}")


def get_random_str(k=32):
  return base64.urlsafe_b64decode(secrets.token_bytes(k)).rstrip(b'=').decode("utf-8")

@user_router.post("/update_accession")
async def update_accession(accession: UpdateAccession):
  return