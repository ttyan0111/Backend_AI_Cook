"""
User Route Handlers - Extracted from routes/user/
All user-related route handlers consolidated here
"""
from fastapi import HTTPException, Body
from core.user_management.service import UserDataService, user_helper
from core.auth.dependencies import extract_user_email, get_user_by_email
from models.user_model import UserOut
from bson import ObjectId
from typing import Dict, Any, List
from datetime import datetime, timezone

# FIXED: Use async MongoDB client (Motor) to match async functions
import os
import motor.motor_asyncio
from dotenv import load_dotenv

load_dotenv()

# Use same database config as main.py but with async client
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DATABASE_NAME", "cook_app")

# Async MongoDB client (Motor)
client = motor.motor_asyncio.AsyncIOMotorClient(
    MONGODB_URI,
    tls=True,
    serverSelectionTimeoutMS=30000,
)
db = client[DB_NAME]

# Async collections
users_collection = db["users"]
user_social_collection = db["user_social"] 
user_activity_collection = db["user_activity"]
user_notifications_collection = db["user_notifications"]
user_preferences_collection = db["user_preferences"]
dishes_collection = db["dishes"]


# ==================== PROFILE HANDLERS ====================

async def create_user_handler(decoded):
    """
    Tạo user mới từ Firebase token (tự động được gọi khi login lần đầu)
    """
    email = decoded.get("email")
    uid = decoded.get("uid")
    name = decoded.get("name", "")
    avatar = decoded.get("picture", "")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required from Firebase token")

    # Kiểm tra user đã tồn tại chưa
    existing_user = await users_collection.find_one({"email": email})
    if existing_user:
        return user_helper(existing_user)

    # Tạo display_id từ email
    display_id = email.split('@')[0]
    
    # Kiểm tra display_id trùng
    counter = 1
    original_display_id = display_id
    while await users_collection.find_one({"display_id": display_id}):
        display_id = f"{original_display_id}{counter}"
        counter += 1

    # Tạo user mới
    user_data = {
        "email": email,
        "display_id": display_id,
        "name": name,
        "avatar": avatar,
        "bio": "",
        "firebase_uid": uid,
        "createdAt": datetime.now(timezone.utc),
        "lastLoginAt": datetime.now(timezone.utc),
    }

    result = await users_collection.insert_one(user_data)
    new_user = await users_collection.find_one({"_id": result.inserted_id})
    
    # Khởi tạo các collections phụ cho user
    await UserDataService.init_user_data(str(new_user["_id"]))

    return user_helper(new_user)


async def get_user_handler(user_id: str):
    """
    Lấy thông tin user theo ID (public)
    """
    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user_helper(user)


async def get_me_handler(decoded):
    """
    Lấy thông tin người dùng hiện tại (tự động tạo nếu chưa có)
    """
    print(f"🔍 get_me_handler called with decoded: {decoded}")
    email = extract_user_email(decoded)
    print(f"📧 Extracted email: {email}")
    
    # Thử tìm user trước - async call
    user = await users_collection.find_one({"email": email})
    print(f"👤 Found existing user: {user is not None}")

    if not user:
        # Tự động tạo user mới nếu chưa tồn tại (first-time login)
        print("🔥 Creating new user...")
        uid = decoded.get("uid")
        name = decoded.get("name", "")
        avatar = decoded.get("picture", "")
        
        # Tạo display_id từ email
        display_id = email.split('@')[0] if email else f"user_{uid[:8]}"
        print(f"🆔 Generated display_id: {display_id}")
        
        # Kiểm tra display_id trùng - async call
        counter = 1
        original_display_id = display_id
        while await users_collection.find_one({"display_id": display_id}):
            display_id = f"{original_display_id}{counter}"
            counter += 1

        # Tạo user mới
        from datetime import datetime, timezone
        user_data = {
            "email": email,
            "display_id": display_id,
            "name": name,
            "avatar": avatar,
            "bio": "",
            "firebase_uid": uid,
            "createdAt": datetime.now(timezone.utc),
            "lastLoginAt": datetime.now(timezone.utc),
        }
        print(f"💾 Inserting user data: {user_data}")

        # async call
        result = await users_collection.insert_one(user_data)
        user = await users_collection.find_one({"_id": result.inserted_id})
        print(f"✅ User created successfully: {user['email']}")
        
        # Khởi tạo các collections phụ cho user mới - async call
        await UserDataService.init_user_data(str(user["_id"]))
        print("📋 User data collections initialized")
    else:
        # Cập nhật lastLoginAt cho user đã tồn tại - async call
        print("♻️ User exists, updating lastLoginAt...")
        from datetime import datetime, timezone
        await users_collection.update_one(
            {"email": email}, 
            {"$set": {"lastLoginAt": datetime.now(timezone.utc)}}
        )
    
    print(f"🎯 Returning user_helper result for: {user['email']}")
    return user_helper(user)
async def update_me_handler(user_update: dict, decoded):
    """
    Cập nhật thông tin cá nhân
    """
    email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Loại bỏ các field không được phép edit
    user_update.pop("email", None)
    user_update.pop("hashed_password", None)
    user_update.pop("firebase_uid", None)
    
    # Kiểm tra display_id trùng
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


async def search_users_handler(q: str, decoded):
    """
    Tìm kiếm người dùng theo display_id
    """
    email = extract_user_email(decoded)
    current_user = await users_collection.find_one({"email": email})
    
    query = {
        "display_id": {"$regex": q, "$options": "i"},
        "_id": {"$ne": current_user["_id"]}  
    }
    users = await users_collection.find(query).to_list(length=20)
    return [user_helper(u) for u in users]


# ==================== SOCIAL HANDLERS ====================

async def get_my_social_handler(decoded):
    """
    Lấy thông tin social của user hiện tại
    """
    email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    social_data = await UserDataService.get_user_social(str(user["_id"]))
    return social_data.dict() if social_data else {
        "followers": [], "following": [], "follower_count": 0, "following_count": 0
    }


async def follow_user_handler(user_id: str, decoded):
    """
    Theo dõi người dùng khác
    """
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    email = extract_user_email(decoded)
    user_to_follow = await users_collection.find_one({"_id": ObjectId(user_id)})
    current_user = await users_collection.find_one({"email": email})

    if not user_to_follow or not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user["_id"] == user_to_follow["_id"]:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")
    
    result = await UserDataService.follow_user(str(current_user["_id"]), user_id)   
 
    # Gửi thông báo milestone nếu cần
    social_data = await UserDataService.get_user_social(user_id)
    if social_data and social_data.follower_count % 5 == 0:
        # TODO: Implement milestone notification
        pass
    
    return {"msg": f"You are now following {user_to_follow['display_id']}"}


async def get_user_dishes_handler(user_id: str):
    """
    Xem danh sách món ăn đã tạo của người dùng khác
    """
    dishes = await dishes_collection.find({"creator_id": user_id}).to_list(length=20)
    return dishes


# ==================== ACTIVITY HANDLERS ====================

MAX_HISTORY = 50

async def get_my_activity_handler(decoded):
    """
    Lấy activity history của user hiện tại
    """
    email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    activity_data = await UserDataService.get_user_activity(str(user["_id"]))
    return activity_data.dict() if activity_data else {
        "favorite_dishes": [], "cooked_dishes": [], "viewed_dishes": [], 
        "created_recipes": [], "created_dishes": []
    }


async def add_cooked_dish_handler(dish_id: str, decoded):
    """
    Thêm món vào lịch sử đã nấu
    """
    email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await UserDataService.add_to_cooked(str(user["_id"]), dish_id, MAX_HISTORY)
    return result


async def add_viewed_dish_handler(dish_id: str, decoded):
    """
    Thêm món vào lịch sử đã xem
    """
    email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await UserDataService.add_to_viewed(str(user["_id"]), dish_id, MAX_HISTORY)
    return result


async def notify_favorite_handler(dish_id: str):
    """
    Gửi thông báo khi có người thả tim món ăn 
    """
    dish = await dishes_collection.find_one({"_id": ObjectId(dish_id)})
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")
    
    creator_id = dish.get("creator_id")
    if not creator_id:
        return {"msg": "No creator for this dish"}
    
    # Đếm số lượt favorite
    favorite_count = 0
    async for activity in user_activity_collection.find({}):
        if dish_id in activity.get("favorite_dishes", []):
            favorite_count += 1
    
    # Gửi thông báo milestone
    if favorite_count % 5 == 0:
        await user_notifications_collection.update_one(
            {"user_id": creator_id},
            {
                "$push": {"notifications": {
                    "type": "milestone",
                    "message": f"Món ăn '{dish['name']}' của bạn đã nhận được {favorite_count} lượt thả tim!",
                    "created_at": "now",
                    "read": False
                }},
                "$inc": {"unread_count": 1}
            },
            upsert=True
        )
    return {"msg": "Notification sent if milestone reached"}


# ==================== PREFERENCES HANDLERS ====================

async def get_my_notifications_handler(decoded):
    """
    Lấy thông báo của user hiện tại
    """
    email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    notif_data = await UserDataService.get_user_notifications(str(user["_id"]))
    return notif_data.dict() if notif_data else {"notifications": [], "unread_count": 0}


async def set_reminders_handler(reminders: List[str], decoded):
    """
    Đặt thời gian nhắc nhở
    """
    email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await user_preferences_collection.update_one(
        {"user_id": str(user["_id"])},
        {"$set": {"reminders": reminders}},
        upsert=True
    )
    return {"msg": "Reminders set successfully"}


async def get_reminders_handler(decoded):
    """
    Lấy danh sách thời gian nhắc nhở
    """
    email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    preferences = await user_preferences_collection.find_one({"user_id": str(user["_id"])})
    return preferences.get("reminders", []) if preferences else []
