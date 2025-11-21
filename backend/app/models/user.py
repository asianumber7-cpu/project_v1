from sqlalchemy import Column, Integer, String
from sqlalchemy.types import JSON  # JSON 타입을 임포트
from app.db.database import Base  # 3-1에서 만든 Base 임포트

class User(Base):
    __tablename__ = "users"  # 테이블 이름

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    # 사용자의 신체 사이즈를 JSON 형태로 저장
    # 예: {"height": 175, "weight": 70, "waist": 30}
    body_size = Column(JSON, nullable=True)