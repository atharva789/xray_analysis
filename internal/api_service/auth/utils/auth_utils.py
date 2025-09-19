from bcrypt import checkpw, hashpw, gensalt

def verify_password(plain_password: str, hashed_password: str) -> bool:
  try:
    return checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
  except ValueError:
    return False
    
    
def get_password_hash(plain_password: str) -> str:
  return hashpw(plain_password.encode("utf-8"), gensalt()).decode("utf-8")
