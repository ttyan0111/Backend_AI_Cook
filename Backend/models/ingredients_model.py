from pydantic import BaseModel, Field
from typing import List

class IngredientOut(BaseModel):
    id: str = Field(..., example="abc123")
    name: str = Field(..., example="Beef")
    category: str = Field(..., example="Meat")
    aliases: List[str] = Field(default_factory=list, example=["bo", "bò", "beef"])