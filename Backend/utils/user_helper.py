def user_helper(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "display_id": user["display_id"],
        "followers": user.get("followers", []),
        "following": user.get("following", []),
        "recipes": user.get("recipes", []),
        "liked_dishes": user.get("liked_dishes", []),
        "favorite_dishes": user.get("favorite_dishes", [])
    }
