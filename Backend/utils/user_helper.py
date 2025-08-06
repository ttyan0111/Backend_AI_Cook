def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "display_id": user["display_id"],
        "followers": user.get("followers", []),
        "following": user.get("following", []),
        "recipes": user.get("recipes", []),
        "favorite_dishes": user.get("favorite_dishes", []),
        "cooked_dishes": user.get("cooked_dishes", []),
        "viewed_dishes": user.get("viewed_dishes", []),
        "notifications": user.get("notifications", [])
    }