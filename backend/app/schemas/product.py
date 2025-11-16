# backend/app/schemas/product.py

from pydantic import BaseModel
from typing import Dict, Any

# 1. 공통 속성을 정의하는 Base 모델
class ProductBase(BaseModel):
    name: str
    description: str | None = None
    image_url: str
    
    # 예: {"S": 10, "M": 20, "L": 5} (사이즈: 재고)
    size_info: Dict[str, Any] | None = None

# 2. 상품 생성 시 받을 데이터 (Create)
class ProductCreate(ProductBase):
    pass  # 지금은 Base와 동일

# 3. DB에서 읽어와 API로 응답할 데이터 (Read)
class Product(ProductBase):
    id: int  # DB에서 생성된 ID 포함

    class Config:
        from_attributes = True  # SQLAlchemy 모델 객체를 Pydantic 모델로 자동 변환