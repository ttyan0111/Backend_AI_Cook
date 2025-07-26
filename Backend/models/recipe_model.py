from pydantic import BaseModel
from typing import List, Optional

class Ingredient(BaseModel):
    name: str
    quantity: str

class Recipe(BaseModel):
    title: str
    description: str
    ingredients: List[Ingredient]
    steps: List[str]
    tags: Optional[List[str]] = []
