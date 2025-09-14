import numpy as np

with open("/Users/attiksh/Documents/BMIL/CAC Prj/CA002-2/mask/1", "rb") as f:
    raw = f.read()

arr = np.frombuffer(raw, dtype=np.uint8)
print("Total bytes:", arr.size)