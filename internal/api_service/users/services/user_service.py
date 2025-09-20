from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from auth.utils.auth_utils import get_password_hash
from users.models.accounts import Accounts
from users.models.users import User


async def get_user_by_email(email: str, session: AsyncSession) -> Accounts | None:
  result = await session.execute(
    text("SELECT * FROM ACCOUNTS WHERE EMAIL=:email"),
    {"email": email}
  )
  record = result.mappings().first()
  if record is None:
    return None
  normalized_record = {key.lower(): value for key, value in record.items()}
  return Accounts(**normalized_record)


async def create_user(user: User, session: AsyncSession) -> Accounts:
  """Create a new account record and return the persisted account."""
  hashed_pwd = get_password_hash(user.password)
  result = await session.execute(
    text(
      """
      INSERT INTO ACCOUNTS (USERNAME, EMAIL, FNAME, LNAME, PSWRD_HASH, DOB)
      VALUES (:username, :email, :f_name, :l_name, :hashed_pwd, :dob)
      RETURNING *
      """
    ),
    {
      "username": user.username,
      "hashed_pwd": hashed_pwd,
      "f_name": user.fname,
      "l_name": user.lname,
      "email": user.email,
      "dob": user.dob
    }
  )
  record = result.mappings().first()
  if record is None:
    raise RuntimeError("Failed to create user account")
  normalized_record = {key.lower(): value for key, value in record.items()}
  return Accounts(**normalized_record)
