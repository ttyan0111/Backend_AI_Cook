from fastapi import FastAPI
from routes import auth_route, recipe_route

app = FastAPI()

app.include_router(auth_route.router)
app.include_router(recipe_route.router)