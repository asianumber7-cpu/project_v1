from pydantic import BaseModel
from typing import Dict, Any, Optional

# 1. 공통 속성
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    size_info: Optional[Dict[str, Any]] = None

    # ★ [추가] JSON 데이터 필드들 ★
    price: Optional[int] = None
    brand: Optional[str] = None
    color: Optional[str] = None
    season: Optional[str] = None

# 2. 생성 (Create)
class ProductCreate(ProductBase):
    pass

# 3. 읽기 (Read)
class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True