from pydantic import BaseModel
from datetime import date

class Accounts(BaseModel):
  aid: int