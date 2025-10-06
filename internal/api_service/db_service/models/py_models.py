from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class BaseFile(BaseModel):
  object_key: Optional[str]
  type: str
    
class FileResponse(BaseFile):
  s3_url: Optional[str]   

    
class BaseAccession(BaseModel):
  aid: int
  dicom_name: str

class ReadAccession(BaseAccession):
  created_at: datetime
  files: List[FileResponse]
  agaston_score: Optional[int]
  
class DBAccession(BaseAccession):
  created_at:datetime
  file: FileResponse
  agaston_score: int
  
class WriteAccession(BaseAccession):
  aid: int
  agaston_score: int = -1
  files: List[BaseFile]
  
class UpdateAccession(BaseModel):
  dicom_name: str
  files: List[BaseFile]