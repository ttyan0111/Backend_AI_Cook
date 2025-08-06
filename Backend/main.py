from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import user_route, dish_route, recipe_route, auth_route

app = FastAPI()

# Add routers
app.include_router(auth_route.router, prefix="/auth", tags=["Authentication"])
app.include_router(user_route.router, prefix="/users", tags=["Users"])
app.include_router(dish_route.router, prefix="/dishes", tags=["Dishes"])
app.include_router(recipe_route.router, prefix="/recipes", tags=["Recipes"])

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)