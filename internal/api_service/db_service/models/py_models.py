from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class File(BaseModel):
  object_key: Optional[str]
  type: str
  data: bytes
    
class BaseAccession(BaseModel):
  aid: int
  dicom_name: str

class ReadAccession(BaseAccession):
  created_at: datetime
  files: List[File]
  agaston_score: Optional[int]
  
  
class WriteAccession(BaseAccession):
  aid: int
  agaston_score: int = -1
  files: List[File]
  
class UpdateAccession(BaseModel):
  dicom_name: str
  files: List[File]