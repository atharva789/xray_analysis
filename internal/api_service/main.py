from cloud_services import *
from fastapi import FastAPI, Request,Depends
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import os

from auth.routes.auth_router import auth_router
from users.routes.user_router import user_router

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
  
  
  # create tables is a SYNCHRONOUS method
  # so we need to run with run_sync
  
  async with engine.begin() as conn:
    await conn.run_sync(SQLModel.metadata.create_all)
  
  app.state.db_engine = engine
  app.state.sessionmaker = session_maker
  app.state.s3_client = client
  app.state.s3_bucket_name = bucket_name
  
  try:
    yield
  finally:
    await engine.dispose()
    
    

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/user")


@app.get("/test")
async def get_home():
  return {"Hello": "World"}