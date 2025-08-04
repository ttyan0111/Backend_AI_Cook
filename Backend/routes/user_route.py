from fastapi import APIRouter, HTTPException, Depends, Body
from models.user_model import UserCreate, UserOut
from utils.user_helper import user_helper
from database.mongo import users_collection, dishes_collection
from passlib.context import CryptContext
from bson import ObjectId
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os
from typing import List


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

# Helper: lấy user từ email
async def get_user_by_email(user_email: str):
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# POST /users/ dùng tạo mới một user (đăng ký)
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

# GET /users/{user_id} dùng để lấy thông tin của một user theo ID
@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str):
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user_helper(user)


# GET /users/me dùng để lấy thông tin của người dùng hiện tại
@router.get("/me", response_model=UserOut)
async def get_me(user_email: str = Depends(get_current_user)):
    user = await get_user_by_email(user_email)
    return user_helper(user)


# POST /users/{user_id}/follow dùng để người dùng theo dõi người khác
@router.post("/{user_id}/follow")
async def follow_user(user_id: str, current_email: str = Depends(get_current_user)):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    user_to_follow = await users_collection.find_one({"_id": ObjectId(user_id)})
    current_user = await get_user_by_email(current_email)

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


# ================== FOLLOW & SOCIAL ==================

#người dùng search tên của người dùng khác
@router.get("/search/")
async def search_users(q: str):
    users = await users_collection.find({"display_id": {"$regex": q, "$options": "i"}}).to_list(length=20)
    return [user_helper(u) for u in users]
#xem danh sách món ăn đã tạo của người dùng khác
@router.get("/{user_id}/dishes")
async def get_user_dishes(user_id: str):
    dishes = await dishes_collection.find({"creator_id": user_id}).to_list(length=20)
    return dishes



# ================== USER PROFILE ==================
#cho phep nguoi dung chinh sua thong tin ca nhan
@router.put("/me", response_model=UserOut)
async def update_me(
    user_update: dict = Body(...),
    user_email: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_update.pop("email", None)
    user_update.pop("hashed_password", None)
    if "display_id" in user_update:
        existing = await users_collection.find_one({"display_id": user_update["display_id"]})
        if existing and existing["_id"] != user["_id"]:
            raise HTTPException(status_code=400, detail="Display ID already taken")
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": user_update}
    )
    updated_user = await users_collection.find_one({"_id": user["_id"]})
    return user_helper(updated_user)

# ================== PASSWORD MANAGEMENT ==================
# Đổi mật khẩu
@router.put("/me/password")
async def change_password(
    old_password: str = Body(...),
    new_password: str = Body(...),
    user_email: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not pwd_context.verify(old_password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    new_hashed = pwd_context.hash(new_password)
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"hashed_password": new_hashed}}
    )
    return {"msg": "Password updated successfully"}


# ================== COOKED HISTORY ==================
@router.post("/me/cooked/{dish_id}")
async def add_cooked_dish(dish_id: str, user_email: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$addToSet": {"cooked_dishes": dish_id}}
    )
    return {"msg": "Dish added to cooked history"}

@router.get("/me/cooked", response_model=List[str])
async def get_cooked_history(user_email: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.get("cooked_dishes", [])


# ================== REMINDERS & NOTIFICATIONS ==================
# Đặt thời gian nhắc nhở
@router.post("/me/reminders")
async def set_reminders(
    reminders: List[str] = Body(..., example=["07:00", "18:30"]),
    user_email: str = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"reminders": reminders}}
    )
    return {"msg": "Reminders set successfully"}

# Lấy danh sách thời gian nhắc nhở
@router.get("/me/reminders", response_model=List[str])
async def get_reminders(user_email: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.get("reminders", [])


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
        {"_id": current_user["_id"]},
        {"$addToSet": {"following": user_to_follow["_id"]}}
    )
    await users_collection.update_one(
        {"_id": user_to_follow["_id"]},
        {"$addToSet": {"followers": current_user["_id"]}}
    )

    user = await users_collection.find_one({"_id": user_to_follow["_id"]})
    followers_count = len(user.get("followers", []))
    if followers_count % 5 == 0:
        await users_collection.update_one(
            {"_id": user_to_follow["_id"]},
            {"$push": {"notifications": f"Bạn đã đạt {followers_count} người theo dõi!"}}
        )
    return {"msg": f"You are now following {user_to_follow['display_id']}"}

# Gửi thông báo khi có người thả tim món ăn 

@router.post("/notify-favorite/{dish_id}")
async def notify_favorite(dish_id: str):
    dish = await dishes_collection.find_one({"_id": ObjectId(dish_id)})
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")
    creator_id = dish.get("creator_id")
    if not creator_id:
        return {"msg": "No creator for this dish"}
    favorite_count = sum([dish_id in u.get("favorite_dishes", []) for u in await users_collection.find().to_list(length=1000)])
    if favorite_count % 5 == 0:
        await users_collection.update_one(
            {"_id": ObjectId(creator_id)},
            {"$push": {"notifications": f"Món ăn '{dish['name']}' của bạn đã nhận được {favorite_count} lượt thả tim!"}}
        )
    return {"msg": "Notification sent if milestone reached"}