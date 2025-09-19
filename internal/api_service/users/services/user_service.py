from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from internal.api_service.auth.utils.auth_utils import get_password_hash
from internal.api_service.users.models.accounts import Accounts

from internal.api_service.main import get_rw_session, get_session
from internal.api_service.users.models.accounts import Accounts


async def get_user_by_email(email: str, session: AsyncSession = Depends[get_session]):
  result = await session.execute(
    text("SELECT * FROM ACCOUNTS WHERE EMAIL=:email"),
    {"email": email}
  )
  record = result.mappings().first()
  account = Accounts(**record)
  return account # there should only be one email

def create_user(user: Accounts, session: AsyncSession = Depends[get_rw_session]):
  """
  inputs a struct of type 'User' and returns the Db struct of type
  'Accounts'
  """
  hashed_pwd = get_password_hash(user.password)
  result = session.execute(
    text(
"""INSERT INTO ACCOUNTS (USERNAME, EMAIL, FNAME, LNAME, PSWRD_HASH, DOB)
VALUES (username, email, f_name, l_name, hashed_pwd, dob)
"""),
    {
      "username": user.username,
      "hashed_pwd": hashed_pwd,
      "f_name": user.fname,
      "l_name": user.lname,
      "email": user.email,
      "dob": user.dob
    }
  )
  account = result.mappings().first()
  account = Accounts(**account)
  return account
