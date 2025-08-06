from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DishIn(BaseModel):
    name: str
    image_url: str
    ingredients: List[str]
    cooking_time: int
    ratings: List[int] = Field(default_factory=list)
    average_rating: Optional[float] = 0.0
    liked_by: List[str] = Field(default_factory=list)

    
class Dish(DishIn):
    id: Optional[str] = Field(default=None, alias="_id")  
    creator_id: Optional[str] = None  # Thêm creator_id
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True 
        arbitrary_types_allowed = True
        validate_by_name = True

class DishOut(BaseModel):
    id: str
    name: str
    image_url: str
    cooking_time: int
    average_rating: float

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
