from typing import Annotated
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from internal.api_service.users.models.accounts import Accounts
import jwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession
from internal.api_service.auth.models.token import TokenData
from internal.api_service.auth.utils.auth_utils import verify_password
from internal.api_service.users.services.user_service import get_user_by_email
from internal.api_service.main import get_session
import os
from datetime import datetime, timedelta, timezone

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def _require_secret_key() -> str:
  if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable is not set")
  return JWT_SECRET_KEY


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
  secret_key = _require_secret_key()
  to_encode = data.copy()
  expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
  to_encode.update({"exp": expire})
  encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
  return encoded_jwt


async def authenticate_user(email: str, password: str, session: AsyncSession) -> Accounts | None:
  """Validate user credentials and return the matching account."""
  user = await get_user_by_email(email, session)
  if not user:
    return None
  if not verify_password(password, user.pswrd_hash):
    return None
  return user


async def get_current_user(
  token: Annotated[str, Depends(oauth2_scheme)],
  session: AsyncSession = Depends(get_session)
) -> Accounts:
  """Get the current user from the JWT token."""
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
  )

  try:
    payload = jwt.decode(token, _require_secret_key(), algorithms=[ALGORITHM])
    email: str | None = payload.get("sub")
    if email is None:
      raise credentials_exception
    token_data = TokenData(email=email)
  except InvalidTokenError:
    raise credentials_exception

  user = await get_user_by_email(email=token_data.email, session=session)
  if user is None:
    raise credentials_exception
  return user


async def get_current_active_user(current_user: Accounts = Depends(get_current_user)) -> Accounts:
  return current_user
