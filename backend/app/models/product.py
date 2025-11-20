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
    
    # 텍스트 벡터
    text_vector = Column(JSON, nullable=True)
    
    # ★ [수정] JSON 데이터에 맞춰 컬럼 추가/수정 ★
    price = Column(Integer, nullable=True)
    brand = Column(String(50), index=True, nullable=True)  # JSON의 "brand" 대응
    color = Column(String(50), nullable=True)              # JSON의 "color" 대응
    season = Column(String(20), nullable=True)             # JSON의 "season" 대응
    
    # category는 JSON에 없지만 나중을 위해 남겨두어도 됩니다 (필수 아님)
    category = Column(String(50), nullable=True)

    # 관계 설정
    vectors = relationship("ProductVector", back_populates="product")