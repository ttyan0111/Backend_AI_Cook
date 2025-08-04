from fastapi import APIRouter, HTTPException, Depends
from models.dish_model import Dish, DishOut, DishIn
from database.mongo import dishes_collection
from bson import ObjectId
from datetime import datetime
from routes.user_route import get_current_user

router = APIRouter()

# Tạo món ăn mới
@router.post("/", response_model=DishOut)
async def create_dish(dish: DishIn):
    new_dish = dish.dict()
    new_dish["created_at"] = datetime.utcnow()
    result = await dishes_collection.insert_one(new_dish)
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Insert failed")
    new_id = result.inserted_id
    return DishOut(
        id=str(new_id),
        name=new_dish["name"],
        image_url=new_dish["image_url"],
        cooking_time=new_dish["cooking_time"],
        average_rating=new_dish.get("average_rating", 0.0),
    )
# Lấy danh sách món ăn
@router.get("/", response_model=list[DishOut])
async def get_dishes():
    cursor = dishes_collection.find().sort("created_at", -1).limit(20)
    dishes = await cursor.to_list(length=20)
    return [
        DishOut(
            id=str(d.get("_id", "")),
            name=d.get("name", ""),
            image_url=d.get("image_url", ""),
            cooking_time=d.get("cooking_time", 0),
            average_rating=d.get("average_rating", 0.0),
        )
        for d in dishes
    ]


##cho ng dùng đánh giá món ăn
@router.post("/{dish_id}/rate")
async def rate_dish(dish_id: str, rating: int, user_email: str = Depends(get_current_user)):
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")
    dish = await dishes_collection.find_one({"_id": ObjectId(dish_id)})
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")
    ratings = dish.get("ratings", [])
    ratings.append(rating)
    average_rating = sum(ratings) / len(ratings)
    await dishes_collection.update_one(
        {"_id": ObjectId(dish_id)},
        {"$set": {"ratings": ratings, "average_rating": average_rating}}
    )
    return {"msg": "Rating added", "average_rating": average_rating}

from database.mongo import users_collection

##người dùng thả tim vào món ăn -> favorite
@router.post("/{dish_id}/favorite")
async def favorite_dish(dish_id: str, user_email: str = Depends(get_current_user)):
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await users_collection.update_one(
        {"email": user_email},
        {"$addToSet": {"favorite_dishes": dish_id}}
    )
    return {"msg": "Dish favorited"}