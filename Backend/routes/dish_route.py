# routers/dishes.py
from fastapi import APIRouter, HTTPException, Depends, Query
from models.dish_model import Dish, DishOut, DishIn
from models.dish_with_recipe_model import DishWithRecipeIn, DishWithRecipeOut
from database.mongo import dishes_collection, users_collection, recipe_collection
from bson import ObjectId
from datetime import datetime
from core.auth.dependencies import get_current_user, get_user_by_email, extract_user_email
from typing import List, Optional, Dict
from pydantic import BaseModel
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os
from dotenv import load_dotenv
import base64
import io
import logging
load_dotenv() 

# Load Cloudinary credentials từ environment variables
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Kiểm tra xem các credentials có đầy đủ không
if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    raise ValueError("Missing Cloudinary credentials. Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in your environment variables.")

# Configure Cloudinary với credentials từ environment
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

print(f"Cloudinary configured with cloud_name: {CLOUDINARY_CLOUD_NAME}")

router = APIRouter()

class RecipeDetailOut(BaseModel):
    id: str
    name: str
    description: str = ""
    ingredients: list = []
    difficulty: str = ""
    instructions: list = []
    average_rating: float = 0.0
    image_url: str = None  # Thay đổi từ image_b64 sang image_url
    created_by: str = None
    dish_id: str = None
    ratings: list = []
    created_at: datetime = None

class DishWithRecipeDetailOut(BaseModel):
    dish: 'DishDetailOut'
    recipe: Optional[RecipeDetailOut] = None

class DishDetailOut(BaseModel):
    id: str
    name: str
    image_url: Optional[str] = None  # Thay đổi từ image_b64 sang image_url
    cooking_time: int
    average_rating: float
    ingredients: List[str] = []
    liked_by: List[str] = []
    creator_id: Optional[str] = None
    recipe_id: Optional[str] = None
    created_at: Optional[datetime] = None


class CheckFavoritesRequest(BaseModel):
    dish_ids: List[str]

def _to_detail_out(d) -> DishDetailOut:
    return DishDetailOut(
        id=str(d["_id"]),
        name=d.get("name", ""),
        image_url=d.get("image_url"),  # Thay đổi từ image_b64 sang image_url
        cooking_time=int(d.get("cooking_time") or 0),
        average_rating=float(d.get("average_rating") or 0.0),
        ingredients=d.get("ingredients") or [],
        liked_by=d.get("liked_by") or [],
        creator_id=d.get("creator_id"),
        recipe_id=d.get("recipe_id"),
        created_at=d.get("created_at"),
    )

def _clean_dish_data(dish_dict: dict) -> dict:
    cleaned = {}
    # bắt buộc
    for k in ["name", "cooking_time", "ingredients"]:
        if k in dish_dict and dish_dict[k] not in (None, "", [], {}):
            cleaned[k] = dish_dict[k]
    # tùy chọn (thay image_b64/image_mime bằng image_url)
    for k in ["image_url", "creator_id", "recipe_id"]:
        if k in dish_dict and dish_dict[k] not in (None, "", [], {}):
            cleaned[k] = dish_dict[k]
    # mặc định
    cleaned.setdefault("ratings", [])
    cleaned.setdefault("average_rating", 0.0)
    cleaned.setdefault("liked_by", [])
    cleaned.setdefault("created_at", datetime.utcnow())
    return cleaned

async def upload_image_to_cloudinary(image_b64: str, image_mime: str, folder: str = "dishes") -> str:
    """
    Upload base64 image to Cloudinary và trả về secure_url
    Sử dụng credentials đã được config ở trên
    """
    try:
        # Debug: Log để kiểm tra credentials
        logging.info(f"Uploading to Cloudinary - Cloud: {CLOUDINARY_CLOUD_NAME}, Folder: {folder}")
        
        # Decode base64 image
        image_data = base64.b64decode(image_b64)
        
        # Upload to Cloudinary sử dụng config đã set
        upload_result = cloudinary.uploader.upload(
    image_data,
    folder=folder,
    resource_type="image",
    transformation=[
        {"quality": "auto:good"},
        {"fetch_format": "auto"}
    ]
)
        
        logging.info(f"Successfully uploaded image: {upload_result['secure_url']}")
        return upload_result["secure_url"]
        
    except Exception as e:
        logging.error(f"Failed to upload image to Cloudinary (Cloud: {CLOUDINARY_CLOUD_NAME}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

def get_optimized_image_url(public_id: str, width: int = None, height: int = None, crop: str = "auto") -> str:
    """
    Tạo optimized image URL từ Cloudinary với các transformation
    """
    try:
        transformations = []
        
        if width and height:
            transformations.append({
                "width": width,
                "height": height,
                "crop": crop,
                "gravity": "auto"
            })
        
        transformations.extend([
            {"quality": "auto:good"},
            {"fetch_format": "auto"}
        ])
        
        optimized_url, _ = cloudinary_url(
            public_id,
            transformation=transformations
        )
        
        return optimized_url
    except Exception as e:
        logging.error(f"Failed to generate optimized URL: {str(e)}")
        return public_id  # Fallback to original URL

# Tạo món (FE gửi JSON có image_b64/image_mime)
@router.post("/", response_model=DishOut)
async def create_dish(dish: DishIn, decoded=Depends(get_current_user)):
    user_email = extract_user_email(decoded)
    user = await get_user_by_email(user_email)

    payload = dish.dict()
    
    # Upload image to Cloudinary if provided
    image_url = None
    if payload.get("image_b64") and payload.get("image_mime"):
        image_url = await upload_image_to_cloudinary(
            payload["image_b64"], 
            payload["image_mime"], 
            folder="dishes"
        )

    new_doc = _clean_dish_data({
        "name": payload["name"],
        "cooking_time": payload["cooking_time"],
        "ingredients": payload.get("ingredients", []),
        "image_url": image_url,  # Lưu URL thay vì base64
        "creator_id": str(user["_id"]),
    })

    result = await dishes_collection.insert_one(new_doc)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Insert failed")

    return DishOut(
        id=str(result.inserted_id),
        name=new_doc["name"],
        cooking_time=new_doc["cooking_time"],
        average_rating=new_doc.get("average_rating", 0.0),
    )

# Tạo dish + recipe (upload ảnh lên Cloudinary)
@router.post("/with-recipe", response_model=DishWithRecipeOut)
async def create_dish_with_recipe(data: DishWithRecipeIn, decoded=Depends(get_current_user)):
    user_email = extract_user_email(decoded)
    user = await get_user_by_email(user_email)

    # Difficulty mapping từ tiếng Việt sang tiếng Anh
    difficulty_map = {
        "Dễ": "easy",
        "Trung bình": "medium", 
        "Khó": "hard"
    }

    image_b64 = getattr(data, "image_b64", None)
    image_mime = getattr(data, "image_mime", None)
    
    # Upload image to Cloudinary if provided
    image_url = None
    if image_b64 and image_mime:
        image_url = await upload_image_to_cloudinary(
            image_b64, 
            image_mime, 
            folder="dishes"
        )

    dish_doc = _clean_dish_data({
        "name": data.name,
        "ingredients": data.ingredients,
        "cooking_time": data.cooking_time,
        "image_url": image_url,  # Lưu URL thay vì base64
        "creator_id": str(user["_id"]),
    })
    
    dish_result = await dishes_collection.insert_one(dish_doc)
    if not dish_result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create dish")

    dish_id = str(dish_result.inserted_id)

    recipe_doc = {
        "name": data.recipe_name or f"Cách làm {data.name}",
        "description": data.recipe_description or f"Hướng dẫn làm {data.name}",
        "ingredients": data.recipe_ingredients or data.ingredients,
        "difficulty": difficulty_map.get(data.difficulty, data.difficulty.lower()),
        "instructions": data.instructions,
        "dish_id": dish_id,
        "created_by": user_email,
        "ratings": [],
        "average_rating": 0.0,
        "image_url": image_url,  # Lưu URL thay vì base64
        "created_at": datetime.utcnow(),
    }
    
    recipe_result = await recipe_collection.insert_one(recipe_doc)
    if not recipe_result.inserted_id:
        await dishes_collection.delete_one({"_id": dish_result.inserted_id})
        raise HTTPException(status_code=500, detail="Failed to create recipe")

    # Cập nhật dish với recipe_id
    await dishes_collection.update_one(
        {"_id": dish_result.inserted_id},
        {"$set": {"recipe_id": str(recipe_result.inserted_id)}}
    )

    return DishWithRecipeOut(
        dish_id=dish_id,
        recipe_id=str(recipe_result.inserted_id),
        dish_name=data.name,
        recipe_name=recipe_doc["name"],
        message=f"Món '{data.name}' và công thức nấu ăn đã được tạo thành công!"
    )

# List
@router.get("/", response_model=List[DishDetailOut])
async def get_dishes(limit: int = 20, skip: int = 0):
    cursor = dishes_collection.find(
        {"name": {"$exists": True, "$ne": ""}}
    ).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_to_detail_out(d) for d in docs]

# Gợi ý hôm nay
@router.get("/suggest/today", response_model=List[DishDetailOut])
async def suggest_today():
    docs = await dishes_collection.find(
        {"name": {"$exists": True, "$ne": ""}}
    ).sort("created_at", -1).limit(12).to_list(length=12)
    return [_to_detail_out(d) for d in docs]

@router.get("/random", response_model=List[DishDetailOut])
async def get_random_dishes(limit: int = 3):
    """
    Lấy ngẫu nhiên các món ăn để làm placeholder cho "Gợi ý món hôm nay"
    """
    try:
        # Sử dụng MongoDB aggregation pipeline để lấy random documents
        pipeline = [
            {"$match": {"name": {"$exists": True, "$ne": ""}}},  # Filter valid dishes
            {"$sample": {"size": limit}},  # Random sampling
        ]
        
        docs = await dishes_collection.aggregate(pipeline).to_list(length=limit)
        return [_to_detail_out(d) for d in docs]
        
    except Exception as e:
        logging.error(f"Error fetching random dishes: {str(e)}")
        # Fallback to regular query if aggregation fails
        cursor = dishes_collection.find(
            {"name": {"$exists": True, "$ne": ""}}
        ).sort("created_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [_to_detail_out(d) for d in docs]
    

# Chi tiết dish (1 cá nhân)
@router.get("/{dish_id}", response_model=DishDetailOut)
async def get_dish_detail(dish_id: str):
    d = await dishes_collection.find_one({"_id": ObjectId(dish_id)})
    if not d:
        raise HTTPException(status_code=404, detail="Dish not found")
    return _to_detail_out(d)


#chi tiết dish cho personalscreen
@router.get("/my-dishes", response_model=List[DishDetailOut])
async def get_my_dishes(
    limit: int = 10,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get dishes created by the current logged-in user"""
    
    user_id = current_user.get("user_id") or current_user.get("id")
    user_email = current_user.get("email")
    
    # Debug log
    print(f"Fetching dishes for user: {user_id} (email: {user_email})")
    

    query_filter = {
        "$or": [
            {"creator_id": user_id},           
            {"creator_id": str(user_id)},      
            {"created_by": user_id},
            {"created_by": user_email},
            {"user_id": user_id},
            {"owner_id": user_id}
        ]
    }
    
    # Debug: Log the query
    print(f"MongoDB query filter: {query_filter}")
    
    # Query dishes created by this user, sorted by creation date (newest first)
    user_dishes_cursor = dishes_collection.find(query_filter).sort("created_at", -1).skip(skip).limit(limit)
    
    dishes = await user_dishes_cursor.to_list(length=limit)
    
    # Debug: Log results
    print(f"Found {len(dishes)} dishes for user {user_id}")
    if dishes:
        print(f"Sample dish: {dishes[0].get('name')} (creator_id: {dishes[0].get('creator_id')})")
    
    return [_to_detail_out(dish) for dish in dishes]

# ✅ ALTERNATIVE: Modify existing dishes endpoint
@router.get("/", response_model=List[DishDetailOut])
async def get_dishes(
    limit: int = 20,
    skip: int = 0,
    my_dishes: bool = False,  # Add this query parameter
    current_user: dict = Depends(get_current_user)
):
    """Get dishes with optional filtering for user's own dishes"""
    
    query = {}
    
    # Filter by current user's dishes if requested
    if my_dishes:
        user_id = current_user.get("user_id") or current_user.get("id")
        query = {
            "$or": [
                {"created_by": user_id},
                {"created_by": current_user.get("email")},
                {"user_id": user_id},
                {"owner_id": user_id}
            ]
        }
    
    dishes_cursor = dishes_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    dishes = await dishes_cursor.to_list(length=limit)
    
    return [_to_detail_out(dish) for dish in dishes]


# Chi tiết dish + recipe
@router.get("/{dish_id}/with-recipe", response_model=DishWithRecipeDetailOut)
async def get_dish_with_recipe(dish_id: str):
    dish = await dishes_collection.find_one({"_id": ObjectId(dish_id)})
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")
    
    recipe = None
    recipe_id = dish.get("recipe_id")
    if recipe_id:
        r = await recipe_collection.find_one({"_id": ObjectId(recipe_id)})
        if r:
            recipe = RecipeDetailOut(
                id=str(r["_id"]),
                name=r.get("name", ""),
                description=r.get("description", ""),
                ingredients=r.get("ingredients", []),
                difficulty=r.get("difficulty", ""),
                instructions=r.get("instructions", []),
                average_rating=float(r.get("average_rating", 0.0)),
                image_url=r.get("image_url"),  # Thay đổi từ image_b64 sang image_url
                created_by=r.get("created_by"),
                dish_id=r.get("dish_id"),
                ratings=r.get("ratings", []),
                created_at=r.get("created_at"),
            )
    
    return DishWithRecipeDetailOut(
        dish=_to_detail_out(dish),
        recipe=recipe
    )

# Đánh giá
@router.post("/{dish_id}/rate")
async def rate_dish(dish_id: str, rating: int, decoded=Depends(get_current_user)):
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")
    d = await dishes_collection.find_one({"_id": ObjectId(dish_id)})
    if not d:
        raise HTTPException(status_code=404, detail="Dish not found")
    ratings = d.get("ratings", [])
    ratings.append(rating)
    avg = sum(ratings) / len(ratings)
    await dishes_collection.update_one(
        {"_id": ObjectId(dish_id)},
        {"$set": {"ratings": ratings, "average_rating": avg}}
    )
    return {"msg": "Rating added", "average_rating": avg}



# Yêu thích
@router.post("/{dish_id}/toggle-favorite")
async def toggle_favorite_dish(dish_id: str, decoded=Depends(get_current_user)):
    user_email = decoded.get("email")
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    favorite_ids = user.get("favorite_dishes") or []
    dish_id_str = str(dish_id)
    if dish_id_str in favorite_ids:
        # Nếu đã yêu thích thì bỏ ra
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$pull": {"favorite_dishes": dish_id_str}}
        )
        return {"isFavorite": False}
    else:
        # Nếu chưa yêu thích thì thêm vào
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$addToSet": {"favorite_dishes": dish_id_str}}
        )
        return {"isFavorite": True}
    

@router.post("/check-favorites", response_model=Dict[str, bool])
async def check_favorites(request: CheckFavoritesRequest, decoded=Depends(get_current_user)):
    """
    Check favorite status for multiple dishes
    Returns a dictionary mapping dish_id -> is_favorite
    """
    try:
        user_email = extract_user_email(decoded)
        user = await get_user_by_email(user_email)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's favorite dishes
        favorite_dish_ids = user.get("favorite_dishes", [])
        
        # Create response dictionary
        result = {}
        for dish_id in request.dish_ids:
            result[dish_id] = dish_id in favorite_dish_ids
            
        return result
        
    except Exception as e:
        logging.error(f"Error checking favorites: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check favorites: {str(e)}")


# Cleanup - cập nhật để xóa cả image_b64 fields cũ
@router.post("/admin/cleanup")
async def cleanup_dishes(decoded=Depends(get_current_user)):
    # Xóa dishes không hợp lệ
    res = await dishes_collection.delete_many({
        "$or": [
            {"name": {"$exists": False}},
            {"name": ""},
            {"name": None}
        ]
    })
    
    # Migration: Xóa các fields image_b64, image_mime cũ (tùy chọn)
    migration_res = await dishes_collection.update_many(
        {},
        {"$unset": {"image_b64": "", "image_mime": ""}}
    )
    
    recipe_migration_res = await recipe_collection.update_many(
        {},
        {"$unset": {"image_b64": "", "image_mime": ""}}
    )
    
    return {
        "deleted_count": res.deleted_count, 
        "dishes_migrated": migration_res.modified_count,
        "recipes_migrated": recipe_migration_res.modified_count,
        "message": "Cleanup and migration completed"
    }

# Utility endpoint để migrate existing data
@router.post("/admin/migrate-images")
async def migrate_existing_images(decoded=Depends(get_current_user)):
    """
    Migrate existing dishes và recipes từ image_b64 sang Cloudinary URLs
    """
    migrated_dishes = 0
    migrated_recipes = 0
    
    # Migrate dishes
    dishes_cursor = dishes_collection.find({"image_b64": {"$exists": True, "$ne": None}})
    async for dish in dishes_cursor:
        try:
            if dish.get("image_b64") and dish.get("image_mime"):
                image_url = await upload_image_to_cloudinary(
                    dish["image_b64"], 
                    dish["image_mime"], 
                    folder="dishes_migration"
                )
                
                await dishes_collection.update_one(
                    {"_id": dish["_id"]},
                    {
                        "$set": {"image_url": image_url},
                        "$unset": {"image_b64": "", "image_mime": ""}
                    }
                )
                migrated_dishes += 1
        except Exception as e:
            logging.error(f"Failed to migrate dish {dish['_id']}: {str(e)}")
    
    # Migrate recipes
    recipes_cursor = recipe_collection.find({"image_b64": {"$exists": True, "$ne": None}})
    async for recipe in recipes_cursor:
        try:
            if recipe.get("image_b64") and recipe.get("image_mime"):
                image_url = await upload_image_to_cloudinary(
                    recipe["image_b64"], 
                    recipe["image_mime"], 
                    folder="recipes_migration"
                )
                
                await recipe_collection.update_one(
                    {"_id": recipe["_id"]},
                    {
                        "$set": {"image_url": image_url},
                        "$unset": {"image_b64": "", "image_mime": ""}
                    }
                )
                migrated_recipes += 1
        except Exception as e:
            logging.error(f"Failed to migrate recipe {recipe['_id']}: {str(e)}")
    
    return {
        "migrated_dishes": migrated_dishes,
        "migrated_recipes": migrated_recipes,
        "message": "Image migration completed"
    }


@router.post("/dishes/{dish_id}/view")
async def log_dish_view(dish_id: str, decoded=Depends(get_current_user)):
    """Log khi user xem chi tiết một món ăn"""
    uid = decoded["uid"]
    now = datetime.now(timezone.utc)

    doc = {
        "type": "dish",
        "id": dish_id,
        "name": "",
        "image": "",
        "ts": now,
    }

    await user_activity_col.update_one(
        {"user_id": uid},
        {"$pull": {"viewed_dishes_and_users": {"type": "dish", "id": dish_id}}},
        upsert=True
    )

    await user_activity_col.update_one(
        {"user_id": uid},
        {
            "$push": {
                "viewed_dishes_and_users": {
                    "$each": [doc],
                    "$position": 0,
                    "$slice": MAX_HISTORY
                }
            },
            "$set": {"updated_at": now}
        },
        upsert=True
    )

    return {"ok": True, "dish_id": dish_id}