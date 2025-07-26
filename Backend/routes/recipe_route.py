from fastapi import APIRouter, Depends, HTTPException
from models.recipe_model import Recipe
from database import recipes_collection
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=["HS256"])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/recipes")
def create_recipe(recipe: Recipe, user_email: str = Depends(get_current_user)):
    recipe_dict = recipe.dict()
    recipe_dict["owner"] = user_email
    recipes_collection.insert_one(recipe_dict)
    return {"msg": "Recipe created"}

@router.get("/recipes")
def get_recipes():
    return list(recipes_collection.find({}, {"_id": 0}))
