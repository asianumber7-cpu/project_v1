# backend/app/schemas/user.py

from pydantic import BaseModel, EmailStr
from typing import Any

# (아이디어 3) 신체 사이즈를 위한 Pydantic 모델
class BodySize(BaseModel):
    height: int | None = None
    weight: int | None = None
    waist: int | None = None

# 회원가입 시 받을 데이터 (Base)
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    body_size: BodySize | None = None  # 신체 사이즈 (선택)

# DB에서 읽어올 때 (비밀번호 제외)
class User(BaseModel):
    id: int
    email: EmailStr
    body_size: BodySize | None = None

    class Config:
        from_attributes = True  # SQLAlchemy 모델을 Pydantic 모델로 자동 변환