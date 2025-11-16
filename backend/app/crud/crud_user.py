# backend/app/crud/crud_user.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

# 이메일로 사용자 조회
async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()

# 사용자 생성 (회원가입)
async def create_user(db: AsyncSession, user: UserCreate):
    # 비밀번호를 해시값으로 변환
    hashed_password = get_password_hash(user.password)
    
    # 신체 사이즈 데이터가 있으면 dict로 변환, 없으면 None
    body_size_data = user.body_size.model_dump() if user.body_size else None
    
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        body_size=body_size_data  # (아이디어 3) DB에 저장
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user