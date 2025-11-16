# backend/app/models/product.py (★ 전체 교체 ★)

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
    
    # ★ 텍스트 벡터 (기존) ★
    text_vector = Column(JSON, nullable=True)
    
    # ★ 새로운 메타데이터 컬럼 추가 ★
    price = Column(Integer, nullable=True)
    color = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)
    season = Column(String(20), nullable=True)
    
    # 관계
    vectors = relationship("ProductVector", back_populates="product")