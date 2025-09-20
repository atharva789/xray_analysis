from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncIterator
from fastapi import Request

def _get_sessionmaker(request: Request) -> async_sessionmaker[AsyncSession]:
  session_maker = getattr(request.app.state, "sessionmaker", None)
  if session_maker is None:
    raise RuntimeError("Database session factory is not configured")
  return session_maker


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
  session_maker = _get_sessionmaker(request)
  async with session_maker() as session:
    yield session # lazy evaluation


async def get_rw_session(request: Request) -> AsyncIterator[AsyncSession]:
  session_maker = _get_sessionmaker(request)
  async with session_maker() as session:
    try:
      yield session
      await session.commit()
    except Exception as e:
      # use kafka for logging later
      print(f"perforning rollback. An error occured while writing: {e}")
      await session.rollback()
