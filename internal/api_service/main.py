from fastapi import FastAPI, Request, Depends
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
import os

from auth.routes.auth_router import auth_router
from auth.services.auth_service import get_current_active_user
from db_service.utils.db_utils import get_session, get_rw_session

db_conn_string = (
  "postgresql+asyncpg://"
  f"{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
  f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}"
  f"/{os.getenv('DB_NAME')}"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
  print("Starting db pool")
  engine = create_async_engine(
    db_conn_string,
    pool_size=10,
    max_overflow=20,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True
  )
  session_maker = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_= AsyncSession
  )

  app.state.db_engine = engine
  app.state.sessionmaker = session_maker
  
  try:
    yield
  finally:
    await engine.dispose()
    
    

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router, prefix="/api")

@app.get("/test")
async def get_home():
  return {"Hello": "World"}


@app.get("/dicoms/{aid}")
async def get_dicoms_by_user(aid: int, session: AsyncSession = Depends[get_session, get_current_active_user]):
  result = await session.execute(
    text("get_dicoms_by_aid"),
    {"aid_input": aid}
  )
  return [dict(row) for row in result.mappings()]

