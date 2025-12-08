from bcrypt import checkpw, hashpw, gensalt

def verify_password(plain_password: str, hashed_password: bytes) -> bool:
  try:
    stored = hashed_password if isinstance(hashed_password, bytes) else hashed_password.encode("utf-8")
    return checkpw(plain_password.encode("utf-8"), stored)
  except ValueError:
    return False
    
    
def get_password_hash(plain_password: str) -> str:
  return hashpw(plain_password.encode("utf-8"), gensalt()).decode("utf-8")
