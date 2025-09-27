from pydantic import BaseModel
from datetime import datetime
from typing import List

class File(BaseModel):
  filetype: str
  object_key: str

class Accession(BaseModel):
  """
  dicom_id should actually be accession_id! 
  Accession is a 'Visitaton' which contains the date it was created, 
  a coned CT, mask, and all statistics related to that session
  """
  created_at: datetime
  name: str
  agaston_score: float
  files: List[File] # load s3 object key