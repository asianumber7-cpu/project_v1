# backend/app/models/product.py

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

    # 상품의 사이즈 재고 등을 JSON으로 저장
    # 예: {"S": 10, "M": 20, "L": 5}
    size_info = Column(JSON, nullable=True)

    # ProductVector 테이블과의 관계 설정
    # 'ProductVector' 모델이 이 상품을 참조할 수 있도록 함
    vectors = relationship("ProductVector", back_populates="product")