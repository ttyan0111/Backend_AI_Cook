from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_id: str

class UserOut(BaseModel):
    id: Optional[str]
    email: EmailStr
    display_id: str
    followers: List[str] = []
    following: List[str] = []
    recipes: List[str] = []
    favorite_dishes: List[str] = []
    cooked_dishes: List[str] = [] 
    notifications: List[str] = []