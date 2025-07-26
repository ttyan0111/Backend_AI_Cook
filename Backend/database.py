#Kết nối Python backend (FastAPI) tới MongoDB Atlas (bản sinh viên siêu provip 5gb nhưng mà chưa biết lấy được k)

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["cook_app"]  # mai sửa thành tên database trên MongoDB
users_collection = db["users"]
recipes_collection = db["recipes"]