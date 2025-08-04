import motor.motor_asyncio
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client["cook_app"]
ingredients_collection = db["ingredients"]
recipe_collection = db["recipes"]
users_collection = db["users"]
dishes_collection = db["dishes"]