# backend/app/api/v1/endpoints/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.db.database import get_db
from app.schemas.user import UserCreate, User
from app.schemas.token import Token
from app.crud import crud_user
from app.core.security import create_access_token, verify_password
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

# 1. 회원가입 API
@router.post("/signup", response_model=User)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return await crud_user.create_user(db=db, user=user)

# 2. 로그인 API (토큰 발급)
@router.post("/token", response_model=Token)
async def login_for_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = await crud_user.get_user_by_email(db, email=form_data.username)
    
    # 이메일(username)이 없거나, 비밀번호가 틀리면 오류
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # JWT 토큰 생성
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}