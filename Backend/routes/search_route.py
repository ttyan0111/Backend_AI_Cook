"""
Search Routes - Find ingredients, users, dishes with filters
"""
from fastapi import APIRouter, Query, HTTPException
from bson.objectid import ObjectId
from database.mongo import ingredients_collection, recipe_collection, users_collection, dishes_collection
from models.ingredients_model import IngredientOut
from models.recipe_model import RecipeOut
from models.user_model import UserOut
from models.dish_model import DishOut
from core.user_management.service import user_helper


router = APIRouter()


# ================== BASIC SEARCH ==================

@router.get("/ingredients", response_model=list[IngredientOut])
async def search_ingredients(q: str = Query(..., min_length=1)):
    """
    Tìm kiếm nguyên liệu theo tên
    """
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


@router.get("/users", response_model=list[UserOut])
async def search_users(q: str = Query(..., min_length=1)):
    """
    Tìm kiếm người dùng theo display_id
    """
    regex = {"$regex": q, "$options": "i"}
    cursor = users_collection.find({"display_id": regex}).limit(10)
    users = await cursor.to_list(length=10)
    
    # Sử dụng user_helper để format consistent với normalized structure
    return [user_helper(u) for u in users]


@router.get("/dishes", response_model=list[DishOut])
async def search_dishes(q: str = Query(..., min_length=1)):
    """
    Tìm kiếm món ăn theo tên
    """
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


@router.get("/recipes", response_model=list[RecipeOut])
async def search_recipes(q: str = Query(..., min_length=1)):
    """
    Tìm kiếm công thức theo tên hoặc mô tả
    """
    regex = {"$regex": q, "$options": "i"}
    cursor = recipe_collection.find({
        "$or": [
            {"name": regex},
            {"description": regex}
        ]
    }).limit(10)
    recipes = await cursor.to_list(length=10)
    return [
        {
            "id": str(r["_id"]),
            "name": r["name"],
            "description": r.get("description", ""),
            "ingredients": r.get("ingredients", []),
            "difficulty": r.get("difficulty", "medium"),
            "image_url": r.get("image_url"),
            "instructions": r.get("instructions", []),
            "dish_id": r.get("dish_id", ""),
            "created_by": r.get("created_by", ""),
            "ratings": r.get("ratings", []),
            "average_rating": r.get("average_rating", 0.0)
        } for r in recipes
    ]


# ================== ADVANCED FILTERS ==================

@router.get("/dishes/by-time", response_model=list[DishOut])
async def filter_dishes_by_time(
    max_time: int = Query(..., description="Thời gian nấu tối đa (phút)", ge=1)
):
    """
    Lọc món ăn theo thời gian nấu
    """
    cursor = dishes_collection.find({"cooking_time": {"$lte": max_time}})
    dishes = await cursor.to_list(length=50)
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


@router.get("/dishes/by-time-rating", response_model=list[DishOut])
async def filter_dishes_by_time_rating(
    max_time: int = Query(..., description="Thời gian nấu tối đa (phút)", ge=1),
    min_rating: float = Query(0.0, description="Rating tối thiểu", ge=0.0, le=5.0)
):
    """
    Lọc món ăn theo thời gian nấu và rating
    """
    cursor = dishes_collection.find({
        "cooking_time": {"$lte": max_time},
        "average_rating": {"$gte": min_rating}
    })
    dishes = await cursor.to_list(length=50)
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


@router.get("/dishes/by-difficulty", response_model=list[DishOut])
async def filter_dishes_by_difficulty(
    difficulty: str = Query(..., description="Độ khó: easy, medium, hard")
):
    """
    Lọc món ăn theo độ khó
    """
    if difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(status_code=400, detail="Invalid difficulty level")
    
    cursor = dishes_collection.find({"difficulty": difficulty})
    dishes = await cursor.to_list(length=50)
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


# ================== COMBINED SEARCH ==================

@router.get("/all")
async def search_all(q: str = Query(..., min_length=2)):
    """
    Tìm kiếm tổng hợp - tất cả loại data
    """
    regex = {"$regex": q, "$options": "i"}
    
    # Search dishes
    dishes_cursor = dishes_collection.find({"name": regex}).limit(5)
    dishes = await dishes_cursor.to_list(length=5)
    
    # Search users
    users_cursor = users_collection.find({"display_id": regex}).limit(5)
    users = await users_cursor.to_list(length=5)
    
    # Search ingredients
    ingredients_cursor = ingredients_collection.find({"name": regex}).limit(5)
    ingredients = await ingredients_cursor.to_list(length=5)
    
    return {
        "dishes": [
            {
                "id": str(d["_id"]),
                "name": d["name"],
                "type": "dish",
                "image_url": d.get("image_url", ""),
                "cooking_time": d.get("cooking_time", 0)
            } for d in dishes
        ],
        "users": [
            {
                "id": str(u["_id"]),
                "name": u.get("name", u["display_id"]),
                "type": "user",
                "display_id": u["display_id"],
                "avatar": u.get("avatar", "")
            } for u in users
        ],
        "ingredients": [
            {
                "id": str(i["_id"]),
                "name": i["name"],
                "type": "ingredient",
                "category": i.get("category", "")
            } for i in ingredients
        ],
        "total_results": len(dishes) + len(users) + len(ingredients)
    }
