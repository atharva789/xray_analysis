from pydantic import BaseModel
from datetime import date

class User(BaseModel):
  aid: int
  username: str
  email: str
  fname: str
  lname: str
  password: str
  dob: date
  created_at: date | None = None