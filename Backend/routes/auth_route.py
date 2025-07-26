# Tạo ra token để xác nhận người dùng đã đăng nhập thành công, và dùng token này để truy cập các route cần xác thực
#Token này chứa thông tin người dùng (email, ID, role…) được mã hóa
#Chỉ server mới có thể giải mã và kiểm tra nó (SECRET_KEY đó chat)

from fastapi import APIRouter, HTTPException, Depends
from models.user_model import UserRegister, UserLogin
from Backend.database import users_collection
from Backend.auth.jwt_handler import create_token, decode_token
from passlib.context import CryptContext

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_current_user(token: str):
    email = decode_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid Token")
    return email

@router.post("/register")
def register(user: UserRegister):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = get_password_hash(user.password)
    users_collection.insert_one({"email": user.email, "password": hashed})
    return {"msg": "User registered"}

@router.post("/login")
def login(user: UserLogin):
    found = users_collection.find_one({"email": user.email})
    if not found or not verify_password(user.password, found["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.email)
    return {"access_token": token}