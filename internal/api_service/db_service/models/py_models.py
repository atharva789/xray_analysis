from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

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
  
  
# ML: request batching & job-scheduling schema

class DicomStats(BaseModel):
  agaston_score: int

class PredictRequest(BaseModel):
  request_id: int
  features: List[List[List[float]]] = Field(..., description="M x N x C image matrix")
  
class PredictResponse(BaseModel):
  request_id: int
  mask: List[List[List[float]]]
  stats: DicomStats
  latency_ms: float

class BatchItem(BaseModel):
  request_id: int
  features: List[List[List[float]]]

class BatchRequest(BaseModel):
  items: List[BatchItem]


class BatchResponseItem(BaseModel):
  request_id: int
  mask: List[List[List[float]]]
  stats: DicomStats

class BatchResponse(BaseModel):
  items: List[BatchResponseItem]
  
