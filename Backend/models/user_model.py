from pydantic import BaseModel

class UserOut(BaseModel):
    id: str
    display_name: str
    bio: str | None = None
    avatar_url: str | None = None