from pydantic import BaseModel
from datetime import date

class Accounts(BaseModel):
  aid: int
  username: str
  email: str
  fname: str
  lname: str
  pswrd_hash: str
  dob: date
  created_at: date | None = None
  