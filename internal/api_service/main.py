import boto3
from fastapi import FastAPI, Request,Depends
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import os

from auth.routes.auth_router import auth_router
from internal.api_service.users.routes import user_router

db_conn_string = (
  "postgresql+asyncpg://"
  f"{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
  f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}"
  f"/{os.getenv('DB_NAME')}"
)
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "pulseimaging-files")

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
  SQLModel.metadata.create_all(engine)
  s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
  )
  app.state.db_engine = engine
  app.state.sessionmaker = session_maker
  app.state.s3_client = s3
  app.state.s3_bucket_name = BUCKET_NAME
  
  try:
    yield
  finally:
    await engine.dispose()
    
    

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/user")

def get_s3(request: Request):
  return request.app.state.s3_client, request.app.state.s3_bucket_name

@app.get("/test")
async def get_home():
  return {"Hello": "World"}