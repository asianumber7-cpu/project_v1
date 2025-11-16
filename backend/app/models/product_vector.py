# backend/app/models/product_vector.py

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from app.db.database import Base

class ProductVector(Base):
    __tablename__ = "product_vectors"

    id = Column(Integer, primary_key=True, index=True)

    # (중요) Product 테이블의 id를 참조하는 외래 키
    product_id = Column(Integer, ForeignKey("products.id"))

    # (★핵심★) AI 모델(CLIP)이 변환한 벡터 값
    # 예: [0.1, 0.5, 0.2, ..., 0.9] (숫자 배열)
    vector = Column(JSON, nullable=False)

    # Product 모델과의 관계 설정
    # 'product'라는 이름으로 Product 모델에 접근 가능
    product = relationship("Product", back_populates="vectors")