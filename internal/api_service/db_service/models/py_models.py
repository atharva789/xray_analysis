from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class BaseFile(BaseModel):
  object_key: Optional[str] = None
  type: str 
  
class UploadNewFile(BaseModel):
  object_key: Optional[str] = ""
  type: str = "slice"
  s3_url: Optional[str] = ""
    
class FileResponse(BaseFile):
  s3_url: Optional[str]   

    
class BaseAccession(BaseModel):
  aid: int
  dicom_name: str

class ReadAccession(BaseAccession):
  dicom_id: int = -1
  created_at: datetime
  files: List[FileResponse]
  agaston_score: Optional[int]
  
class DBAccession(BaseAccession):
  dicom_id: int = -1
  created_at:datetime
  agaston_score: int
  
class WriteAccession(BaseAccession):
  agaston_score: int = -1
  files: List[UploadNewFile]
  
class UpdateAccession(BaseModel):
  dicom_id: int = -1
  dicom_name: str
  files: List[BaseFile]