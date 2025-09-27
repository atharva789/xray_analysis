from pydantic import BaseModel
from datetime import datetime

class Record(BaseModel):
  dicom_id: int
  dicom_name: str
  created_at: datetime
  file_id: int
  filetype: str
  object_key: str
  agaston_score: int