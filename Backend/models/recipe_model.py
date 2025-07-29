from pydantic import BaseModel
from typing import List

class RecipeOut(BaseModel):
    id: str
    name: str
    description: str
    ingredients: List[str]
    difficulty: str
    image_url: str | None = None