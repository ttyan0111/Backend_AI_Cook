#Cho phép người dùng tạo tài khoản và đăng nhập. Nếu thành công, trả về JWT token để xác thực các request sau này

from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str