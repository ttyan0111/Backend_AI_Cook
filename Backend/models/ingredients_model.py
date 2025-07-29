from pydantic import BaseModel

class IngredientOut(BaseModel):
    id: str
    name: str
    category: str
    aliases: list[str]