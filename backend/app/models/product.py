# backend/app/models/product.py (★수정★)

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from app.db.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(String(1000), nullable=True)
    image_url = Column(String(1000), nullable=False)

    size_info = Column(JSON, nullable=True)

    # (★추가★)
    # 상품의 이름(name)과 설명(description)을 AI로 변환한 '텍스트 벡터'
    text_vector = Column(JSON, nullable=True)

    # ProductVector 테이블(이미지 벡터)과의 관계
    vectors = relationship("ProductVector", back_populates="product")