from fastapi import APIRouter, Depends, HTTPException
from models.recipe_model import RecipeIn, RecipeOut
from database.mongo import recipe_collection
from core.auth.dependencies import get_current_user, extract_user_email, get_user_by_email
from bson import ObjectId
from typing import List
from database.mongo import recipe_collection, users_collection

router = APIRouter()

# Tạo công thức mới
@router.post("/", response_model=RecipeOut)
async def create_recipe(recipe: RecipeIn, decoded=Depends(get_current_user)):
    user_email = extract_user_email(decoded)
    # Lấy user để lấy _id
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    recipe_dict = recipe.dict()
    recipe_dict["ratings"] = []
    recipe_dict["average_rating"] = 0.0

    result = await recipe_collection.insert_one(recipe_dict)
    recipe_dict["_id"] = result.inserted_id
    return RecipeOut(id=str(result.inserted_id), **recipe.dict(), average_rating=0.0)

# Lấy công thức theo ID
@router.get("/{recipe_id}", response_model=RecipeOut)
async def get_recipe(recipe_id: str):
    if not ObjectId.is_valid(recipe_id):
        raise HTTPException(status_code=400, detail="Invalid recipe ID")

    recipe = await recipe_collection.find_one({"_id": ObjectId(recipe_id)})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return RecipeOut(
        id=str(recipe["_id"]),
        name=recipe["name"],
        description=recipe.get("description", ""),
        ingredients=recipe["ingredients"],
        difficulty=recipe.get("difficulty", "medium"),
        image_url=recipe.get("image_url"),
        instructions=recipe["instructions"],
        dish_id=recipe["dish_id"],
        created_by=recipe["created_by"],
        ratings=recipe.get("ratings", []),
        average_rating=recipe.get("average_rating", 0.0),
    )

# Lấy công thức của người dùng hiện tại
@router.get("/by-user", response_model=List[RecipeOut])
async def get_recipes_by_user(decoded=Depends(get_current_user)):
    user_email = extract_user_email(decoded)
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    cursor = recipe_collection.find({"created_by": str(user["_id"])})
    recipes = []
    async for recipe in cursor:
        recipes.append(RecipeOut(
            id=str(recipe["_id"]),
            name=recipe["name"],
            description=recipe.get("description", ""),
            ingredients=recipe["ingredients"],
            difficulty=recipe.get("difficulty", "medium"),
            image_url=recipe.get("image_url"),
            instructions=recipe["instructions"],
            dish_id=recipe["dish_id"],
            created_by=recipe["created_by"],
            ratings=recipe.get("ratings", []),
            average_rating=recipe.get("average_rating", 0.0),
        ))
    return recipes



# Đánh giá công thức (thêm sao)
@router.post("/{recipe_id}/rate")
async def rate_recipe(recipe_id: str, rating: int, decoded=Depends(get_current_user)):
    user_email = extract_user_email(decoded)
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    if not ObjectId.is_valid(recipe_id):
        raise HTTPException(status_code=400, detail="Invalid recipe ID")

    recipe = await recipe_collection.find_one({"_id": ObjectId(recipe_id)})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    ratings = recipe.get("ratings", [])
    ratings.append(rating)
    avg = round(sum(ratings) / len(ratings), 2)

    await recipe_collection.update_one(
        {"_id": ObjectId(recipe_id)},
        {"$set": {"ratings": ratings, "average_rating": avg}}
    )

    return {"msg": "Recipe rated successfully", "average_rating": avg}
