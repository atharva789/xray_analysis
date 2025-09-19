from pydantic import BaseModel

class patient(BaseModel): 
  aid: int
  mrn: int