from fastapi import APIRouter, HTTPException
from models.dish_model import Dish, DishOut, DishIn
from database.mongo import dishes_collection
from bson import ObjectId
from datetime import datetime

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