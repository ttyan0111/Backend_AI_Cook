from motor.motor_asyncio import AsyncIOMotorClient
from decouple import config  # hoặc dùng dotenv

MONGO_URI = config("MONGO_URI")

client = AsyncIOMotorClient(MONGO_URI)
db = client["cookapp"]