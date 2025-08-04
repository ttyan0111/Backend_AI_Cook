# firebase_auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth
from functools import lru_cache

# Chỉ khởi tạo Firebase Admin một lần
@lru_cache()
def init_firebase():
    cred = credentials.Certificate("path/to/serviceAccountKey.json")  # <-- đổi path ở đây
    firebase_admin.initialize_app(cred)

# Bảo vệ endpoint bằng Bearer token
security = HTTPBearer()

def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    init_firebase()  # đảm bảo Firebase được khởi tạo
    try:
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token)
        return decoded_token  # chứa 'email', 'uid', v.v.
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token"
        )


##cái này sau này giang đẫm làm dùm