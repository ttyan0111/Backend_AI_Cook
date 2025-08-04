from fastapi import APIRouter, Query
from bson.objectid import ObjectId

from database.mongo import ingredients_collection, recipes_collection, users_collection, dishes_collection
from models.ingredients_model import IngredientOut
from models.recipe_model import RecipeOut
from models.user_model import UserOut
from models.dish_model import DishOut


router = APIRouter()

#tìm ingredients
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
            "unit": i.get("unit", "gram")
        } for i in ingredients
    ]

#tìm người
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
            "favorite_dishes": u.get("favorite_dishes", [])
        } for u in users
    ]

#tìm món ăn
@router.get("/search/dishes", response_model=list[DishOut])
async def search_dishes(q: str = Query(..., min_length=1)):
    regex = {"$regex": q, "$options": "i"}
    cursor = dishes_collection.find({"name": regex}).limit(10)
    dishes = await cursor.to_list(length=10)
    return [
        {
            "id": str(d["_id"]),
            "name": d["name"],
            "image_url": d.get("image_url", ""),
            "cooking_time": d.get("cooking_time", 0),
            "average_rating": d.get("average_rating", 0.0)
        } for d in dishes
    ]
