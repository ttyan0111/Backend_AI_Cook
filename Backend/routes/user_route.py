"""
User Management Routes - Simplified Main Router
All handlers moved to utils.user_handlers for better organization
"""
from fastapi import APIRouter, Depends, Body
from models.user_model import UserOut
from core.auth.dependencies import get_current_user
from utils.user_handlers import (
    # Profile handlers
    create_user_handler,
    get_user_handler, 
    get_me_handler,
    update_me_handler,
    search_users_handler,
    
    # Social handlers
    get_my_social_handler,
    follow_user_handler,
    get_user_dishes_handler,
    
    # Activity handlers
    get_my_activity_handler,
    add_cooked_dish_handler,
    add_viewed_dish_handler,
    notify_favorite_handler,
    get_viewed_dishes_handler,

    # Preferences handlers
    get_my_notifications_handler,
    set_reminders_handler,
    get_reminders_handler
)
from typing import List

# Main router
router = APIRouter()

# ==================== PROFILE ROUTES ====================
@router.post("/", response_model=UserOut)
async def create_user(decoded=Depends(get_current_user)):
    return await create_user_handler(decoded)

@router.get("/me", response_model=UserOut)
async def get_me(decoded=Depends(get_current_user)):
    return await get_me_handler(decoded)

@router.put("/me", response_model=UserOut)
async def update_me(user_update: dict = Body(...), decoded=Depends(get_current_user)):
    return await update_me_handler(user_update, decoded)

@router.get("/search/")
async def search_users(q: str, decoded=Depends(get_current_user)):
    return await search_users_handler(q, decoded)

@router.get("/{user_id}", response_model=UserOut) 
async def get_user(user_id: str):
    return await get_user_handler(user_id)

# ==================== SOCIAL ROUTES ====================
@router.get("/me/social")
async def get_my_social(decoded=Depends(get_current_user)):
    return await get_my_social_handler(decoded)

@router.post("/{user_id}/follow")
async def follow_user(user_id: str, decoded=Depends(get_current_user)):
    return await follow_user_handler(user_id, decoded)

@router.get("/{user_id}/dishes")
async def get_user_dishes(user_id: str):
    return await get_user_dishes_handler(user_id)

# ==================== ACTIVITY ROUTES ====================
@router.get("/me/activity")
async def get_my_activity(decoded=Depends(get_current_user)):
    return await get_my_activity_handler(decoded)

@router.post("/me/cooked/{dish_id}")
async def add_cooked_dish(dish_id: str, decoded=Depends(get_current_user)):
    return await add_cooked_dish_handler(dish_id, decoded)

@router.post("/me/viewed/{dish_id}")
async def add_viewed_dish(dish_id: str, decoded=Depends(get_current_user)):
    return await add_viewed_dish_handler(dish_id, decoded)

@router.get("/me/viewed-dishes")
async def get_viewed_dishes(limit: int = 20, decoded=Depends(get_current_user)):
    return await get_viewed_dishes_handler(limit, decoded)

@router.post("/notify-favorite/{dish_id}")
async def notify_favorite(dish_id: str):
    return await notify_favorite_handler(dish_id)

# ==================== PREFERENCES ROUTES ====================
@router.get("/me/notifications")
async def get_my_notifications(decoded=Depends(get_current_user)):
    return await get_my_notifications_handler(decoded)

@router.post("/me/reminders")
async def set_reminders(reminders: List[str] = Body(...), decoded=Depends(get_current_user)):
    return await set_reminders_handler(reminders, decoded)

@router.get("/me/reminders", response_model=List[str])
async def get_reminders(decoded=Depends(get_current_user)):
    return await get_reminders_handler(decoded)

