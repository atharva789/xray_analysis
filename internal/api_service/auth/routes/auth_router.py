from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models.token import Token
from auth.services.auth_service import authenticate_user, create_access_token
from db_service.utils.db_utils import get_session

from datetime import timedelta

from users.models.accounts import Accounts

auth_router = APIRouter(
  prefix="/auth",
  tags=["Auth"]
)

@auth_router.post("/token")
async def login_for_access_token(
  form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
  session: AsyncSession = Depends(get_session)
) -> Token:
  user: Accounts | None = await authenticate_user(form_data.username, form_data.password, session)
  if not user:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="incorrect email or password",
      headers={"WWW-Authenticate": "Bearer"}
    )
  access_token_expires = timedelta(minutes=30)
  token = create_access_token(
    data={
      "sub": user.email
    },
    expires_delta=access_token_expires
  )
  return Token(access_token=token, token_type="bearer")
