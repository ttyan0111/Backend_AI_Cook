from fastapi import APIRouter, Query
from database import ingredient_collection, recipe_collection, user_collection
from models.ingredients_model import IngredientOut
from models.recipe_model import RecipeOut
from models.user_model import UserOut
from bson.objectid import ObjectId

router = APIRouter()

@router.get("/search/ingredients", response_model=list[IngredientOut])
def search_ingredients(q: str = Query(..., min_length=1)):
    regex = {"$regex": q, "$options": "i"}
    ingredients = ingredient_collection.find({"name": regex}).limit(10)
    return [
        {
            "id": str(i["_id"]),
            "name": i["name"],
            "category": i.get("category", "unknown"),
            "aliases": i.get("aliases", [])
        } for i in ingredients
    ]

@router.get("/search/recipes", response_model=list[RecipeOut])
def search_recipes(q: str = Query(..., min_length=1)):
    regex = {"$regex": q, "$options": "i"}
    recipes = recipe_collection.find({"name": regex}).limit(10)
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
def search_users(q: str = Query(..., min_length=1)):
    regex = {"$regex": q, "$options": "i"}
    users = user_collection.find({"display_name": regex}).limit(10)
    return [
        {
            "id": str(u["_id"]),
            "display_name": u["display_name"],
            "bio": u.get("bio"),
            "avatar_url": u.get("avatar_url")
        } for u in users
    ]