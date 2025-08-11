# routers/dishes.py
from fastapi import APIRouter, HTTPException, Depends, Query
from models.dish_model import Dish, DishOut, DishIn
from models.dish_with_recipe_model import DishWithRecipeIn, DishWithRecipeOut
from database.mongo import dishes_collection, users_collection, recipe_collection
from bson import ObjectId
from datetime import datetime
from core.auth.dependencies import get_current_user, get_user_by_email, extract_user_email
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

class DishDetailOut(BaseModel):
    id: str
    name: str
    image_b64: Optional[str] = None
    image_mime: Optional[str] = None
    cooking_time: int
    average_rating: float
    ingredients: List[str] = []
    liked_by: List[str] = []
    creator_id: Optional[str] = None
    recipe_id: Optional[str] = None
    created_at: Optional[datetime] = None

def _to_detail_out(d) -> DishDetailOut:
    return DishDetailOut(
        id=str(d["_id"]),
        name=d.get("name", ""),
        image_b64=d.get("image_b64"),
        image_mime=d.get("image_mime"),
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
    # tùy chọn (không có image_url)
    for k in ["image_b64", "image_mime", "creator_id", "recipe_id"]:
        if k in dish_dict and dish_dict[k] not in (None, "", [], {}):
            cleaned[k] = dish_dict[k]
    # mặc định
    cleaned.setdefault("ratings", [])
    cleaned.setdefault("average_rating", 0.0)
    cleaned.setdefault("liked_by", [])
    cleaned.setdefault("created_at", datetime.utcnow())
    return cleaned

# Tạo món (FE gửi JSON có image_b64/image_mime)
@router.post("/", response_model=DishOut)
async def create_dish(dish: DishIn, decoded=Depends(get_current_user)):
    user_email = extract_user_email(decoded)
    user = await get_user_by_email(user_email)

    payload = dish.dict()
    new_doc = _clean_dish_data({
        "name": payload["name"],
        "cooking_time": payload["cooking_time"],
        "ingredients": payload.get("ingredients", []),
        "image_b64": payload.get("image_b64"),
        "image_mime": payload.get("image_mime"),
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

# Tạo dish + recipe (giữ ảnh ở cả 2 nếu cần)
@router.post("/with-recipe", response_model=DishWithRecipeOut)
async def create_dish_with_recipe(data: DishWithRecipeIn, decoded=Depends(get_current_user)):
    user_email = extract_user_email(decoded)
    user = await get_user_by_email(user_email)

    image_b64 = getattr(data, "image_b64", None)
    image_mime = getattr(data, "image_mime", None)

    dish_doc = _clean_dish_data({
        "name": data.name,
        "ingredients": data.ingredients,
        "cooking_time": data.cooking_time,
        "image_b64": image_b64,
        "image_mime": image_mime,
        "creator_id": str(user["_id"]),
    })
    dish_result = await dishes_collection.insert_one(dish_doc)
    if not dish_result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create dish")

    dish_id = str(dish_result.inserted_id)

    recipe_doc = {
        "name": data.recipe_name or f"Cách làm {data.name}",
        "description": data.recipe_description,
        "ingredients": data.recipe_ingredients or data.ingredients,
        "difficulty": data.difficulty,
        "instructions": data.instructions,
        "dish_id": dish_id,
        "created_by": user_email,
        "ratings": [],
        "average_rating": 0.0,
        "image_b64": image_b64,
        "image_mime": image_mime,
    }
    recipe_result = await recipe_collection.insert_one(recipe_doc)
    if not recipe_result.inserted_id:
        await dishes_collection.delete_one({"_id": dish_result.inserted_id})
        raise HTTPException(status_code=500, detail="Failed to create recipe")

    await dishes_collection.update_one(
        {"_id": dish_result.inserted_id},
        {"$set": {"recipe_id": str(recipe_result.inserted_id)}}
    )

    return DishWithRecipeOut(
        dish_id=dish_id,
        recipe_id=str(recipe_result.inserted_id),
        dish_name=data.name,
        recipe_name=recipe_doc["name"],
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

# Chi tiết
@router.get("/{dish_id}", response_model=DishDetailOut)
async def get_dish_detail(dish_id: str):
    d = await dishes_collection.find_one({"_id": ObjectId(dish_id)})
    if not d:
        raise HTTPException(status_code=404, detail="Dish not found")
    return _to_detail_out(d)

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
@router.post("/{dish_id}/favorite")
async def favorite_dish(dish_id: str, decoded=Depends(get_current_user)):
    from core.user_management.service import UserDataService
    user_email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await UserDataService.add_to_favorites(str(user["_id"]), dish_id)

# Cleanup
@router.post("/admin/cleanup")
async def cleanup_dishes(decoded=Depends(get_current_user)):
    res = await dishes_collection.delete_many({
        "$or": [
            {"name": {"$exists": False}},
            {"name": ""},
            {"name": None}
        ]
    })
    return {"deleted_count": res.deleted_count, "message": "Cleanup completed"}
