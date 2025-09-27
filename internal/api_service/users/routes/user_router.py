from sqlalchemy import text
from typing_extensions import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models.token import Token
from auth.services.auth_service import authenticate_user, create_access_token
from db_service.utils.db_utils import get_session
from internal.api_service.db_service.models.models import Record
from internal.api_service.users.models.session import Accession, File

user_router = APIRouter(
  prefix="/user",
  tags=["User"]
)
# @app.get("/dicoms/{aid}", dependencies=[Depends(get_current_active_user)], response_model=List[Record])
@user_router.get("/{aid}/sessions", response_model=List[Record])
async def get_dicoms_by_user(aid: int, session: AsyncSession):
  """
  Fetch all 'Accessions' by user
  """
  result = await session.execute(
    text("get_dicoms_by_aid"),
    {"aid_input": aid}
  )
  return [Record(**dict(row)) for row in result.mappings()]


@user_router.get("/{aid}/session", response_model=Accession)
async def get_data_by_session(aid: int, session_id: int, session: AsyncSession):
  """
  Fetch all Coned CTs by Accession (currently called 'Dicoms')
  return (most importantly) 
  """
  result = await session.execute(
    text("get_accession"),
    {"aid_input": aid, "dicom_id_input": session_id}
  )
  res = result.mappings().all()
  accession: Accession
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

@user_router.post("/new_accession")
async def create_accession():
  return