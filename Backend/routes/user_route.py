from fastapi import APIRouter, HTTPException, Depends
from models.user_model import UserCreate, UserOut
from utils.user_helper import user_helper
from database.mongo import users_collection
from passlib.context import CryptContext
from bson import ObjectId
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Auth helper
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# POST /users/
@router.post("/", response_model=UserOut)
async def create_user(user: UserCreate):
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_display = await users_collection.find_one({"display_id": user.display_id})
    if existing_display:
        raise HTTPException(status_code=400, detail="Display ID already taken")

    hashed_password = pwd_context.hash(user.password)

    user_data = {
        "email": user.email,
        "hashed_password": hashed_password,
        "display_id": user.display_id,
        "followers": [],
        "following": [],
        "recipes": [],
        "liked_dishes": [],
        "favorite_dishes": []
    }

    result = await users_collection.insert_one(user_data)
    new_user = await users_collection.find_one({"_id": result.inserted_id})

    return user_helper(new_user)

# GET /users/{user_id}
@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str):
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user_helper(user)

# GET /users/me (lấy thông tin người đang đăng nhập)
@router.get("/me", response_model=UserOut)
async def get_me(user_email: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_helper(user)

# POST /users/{user_id}/follow
@router.post("/{user_id}/follow")
async def follow_user(user_id: str, current_email: str = Depends(get_current_user)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user_to_follow = await users_collection.find_one({"_id": ObjectId(user_id)})
    current_user = await users_collection.find_one({"email": current_email})

    if not user_to_follow or not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user["_id"] == user_to_follow["_id"]:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")

    await users_collection.update_one(
        {"_id": current_user["_id"]}, {"$addToSet": {"following": user_to_follow["_id"]}}
    )
    await users_collection.update_one(
        {"_id": user_to_follow["_id"]}, {"$addToSet": {"followers": current_user["_id"]}}
    )

    return {"msg": f"You are now following {user_to_follow['display_id']}"}
