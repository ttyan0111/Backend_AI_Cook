from fastapi import APIRouter, HTTPException, Depends
from models.dish_model import Dish, DishOut, DishIn
from models.dish_with_recipe_model import DishWithRecipeIn, DishWithRecipeOut
from database.mongo import dishes_collection, users_collection, recipe_collection
from bson import ObjectId
from datetime import datetime
from core.auth.dependencies import get_current_user, get_user_by_email, extract_user_email

router = APIRouter()

# Tạo món ăn và recipe cùng lúc
@router.post("/with-recipe", response_model=DishWithRecipeOut)
async def create_dish_with_recipe(data: DishWithRecipeIn, decoded=Depends(get_current_user)):
    user_email = extract_user_email(decoded)
    user = await get_user_by_email(user_email)
    
    # Tạo dish trước
    dish_data = {
        "name": data.name,
        "image_url": data.image_url,
        "ingredients": data.ingredients,
        "cooking_time": data.cooking_time,
        "ratings": [],
        "average_rating": 0.0,
        "liked_by": [],
        "created_at": datetime.utcnow(),
        "creator_id": str(user["_id"])
    }
    
    dish_result = await dishes_collection.insert_one(dish_data)
    if not dish_result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create dish")
    
    dish_id = str(dish_result.inserted_id)
    
    # Tạo recipe với dish_id vừa tạo
    recipe_data = {
        "name": data.recipe_name or f"Cách làm {data.name}",
        "description": data.recipe_description,
        "ingredients": data.recipe_ingredients or data.ingredients,
        "difficulty": data.difficulty,
        "image_url": data.image_url,
        "instructions": data.instructions,
        "dish_id": dish_id,
        "created_by": user_email,
        "ratings": [],
        "average_rating": 0.0
    }
    
    recipe_result = await recipe_collection.insert_one(recipe_data)
    if not recipe_result.inserted_id:
        # Nếu tạo recipe thất bại, xóa dish đã tạo
        await dishes_collection.delete_one({"_id": dish_result.inserted_id})
        raise HTTPException(status_code=500, detail="Failed to create recipe")
    
    recipe_id = str(recipe_result.inserted_id)
    
    return DishWithRecipeOut(
        dish_id=dish_id,
        recipe_id=recipe_id,
        dish_name=data.name,
        recipe_name=recipe_data["name"]
    )

# Tạo món ăn mới
@router.post("/", response_model=DishOut)
async def create_dish(dish: DishIn, decoded=Depends(get_current_user)):
    user_email = extract_user_email(decoded)
    user = await get_user_by_email(user_email)
    new_dish = dish.dict()
    new_dish["created_at"] = datetime.utcnow()
    new_dish["creator_id"] = str(user["_id"])  # Lưu creator_id là _id của user
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

# ================== RATING & FAV ==================
##cho ng dùng đánh giá món ăn
@router.post("/{dish_id}/rate")
async def rate_dish(dish_id: str, rating: int, decoded=Depends(get_current_user)):
    user_email = extract_user_email(decoded)
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

##người dùng thả tim vào 1 món ăn -> favorite
@router.post("/{dish_id}/favorite")
async def favorite_dish(dish_id: str, decoded=Depends(get_current_user)):
    from core.user_management.service import UserDataService
    
    user_email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ FIXED: Use UserDataService for normalized structure
    result = await UserDataService.add_to_favorites(str(user["_id"]), dish_id)
    return result


