from pydantic import BaseModel
from datetime import date

class Accounts(BaseModel):
  username: str
  email: str
  hashed_pwd: bytes
  fname: str
  lname: str
  email: str
  dob: date