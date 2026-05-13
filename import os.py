import os
from dotenv import load_dotenv

load_dotenv()

print("CWD:", os.getcwd())
print("ENV FILE FOUND:", os.path.exists(".env"))

print("KEY:", os.getenv("APCA_API_KEY_ID"))
print("SECRET:", os.getenv("APCA_API_SECRET_KEY"))