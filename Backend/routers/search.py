from fastapi import APIRouter, Query
from bson.objectid import ObjectId

from database.mongo import ingredients_collection, recipes_collection, users_collection
from models.ingredients_model import IngredientOut
from models.recipe_model import RecipeOut
from models.user_model import UserOut

router = APIRouter()

@router.get("/search/ingredients", response_model=list[IngredientOut])
async def search_ingredients(q: str = Query(..., min_length=1)):
    regex = {"$regex": q, "$options": "i"}
    cursor = ingredients_collection.find({"name": regex}).limit(10)
    ingredients = await cursor.to_list(length=10)
    return [
        {
            "id": str(i["_id"]),
            "name": i["name"],
            "category": i.get("category", "unknown"),
            "unit": i.get("unit", "gram")  # Thêm trường unit nếu cần
        } for i in ingredients
    ]

@router.get("/search/recipes", response_model=list[RecipeOut])
async def search_recipes(q: str = Query(..., min_length=1)):
    regex = {"$regex": q, "$options": "i"}
    cursor = recipes_collection.find({"name": regex}).limit(10)
    recipes = await cursor.to_list(length=10)
    return [
        {
            "id": str(r["_id"]),
            "name": r["name"],
            "description": r.get("description", ""),
            "ingredients": r.get("ingredients", []),
            "difficulty": r.get("difficulty", "medium"),
            "image_url": r.get("image_url")
        } for r in recipes
    ]

@router.get("/search/users", response_model=list[UserOut])
async def search_users(q: str = Query(..., min_length=1)):
    regex = {"$regex": q, "$options": "i"}
    cursor = users_collection.find({"display_id": regex}).limit(10)
    users = await cursor.to_list(length=10)
    return [
        {
            "id": str(u["_id"]),
            "email": u["email"],
            "display_id": u["display_id"],
            "followers": u.get("followers", []),
            "following": u.get("following", []),
            "recipes": u.get("recipes", []),
            "liked_dishes": u.get("liked_dishes", []),
            "favorite_dishes": u.get("favorite_dishes", [])
        } for u in users
    ]
