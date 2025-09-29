import io
import asyncio

class StreamWrapper(io.RawIOBase):
  def __init__(self, stream_iter):
    self.stream_iter = stream_iter
    self.buffer = b""
  
  def readable(self):
    return True
  
  async def fill_buffer(self):
    try:
      chunk = await self.stream_iter.__anext__()
      self.buffer += chunk
    except StopAsyncIteration:
      pass

  
  def read_into(self, b):
    # this method is called by boto3
    loop = asyncio.get_event_loop()
    if not self.buffer:
      loop.run_until_complete(self.fill_buffer())
    if not self.buffer:
      return 0 # EOF
    n = min(len(b), len(self.buffer))
    b[:n] = self.buffer[:n]
    self.buffer = self.buffer[n:]
    return n