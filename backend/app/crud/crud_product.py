# backend/app/crud/crud_product.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.product import Product
from app.schemas.product import ProductCreate

# 1. 특정 ID로 상품 1개 조회
async def get_product(db: AsyncSession, product_id: int):
    result = await db.execute(select(Product).filter(Product.id == product_id))
    return result.scalars().first()

# 2. (페이지네이션) 상품 목록 조회
async def get_products(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Product).offset(skip).limit(limit))
    return result.scalars().all()

# 3. 상품 생성
async def create_product(db: AsyncSession, product: ProductCreate):
    # ProductCreate 스키마를 Product 모델 객체로 변환
    db_product = Product(
        name=product.name,
        description=product.description,
        image_url=product.image_url,
        size_info=product.size_info
    )
    
    db.add(db_product)  # 세션에 추가
    await db.commit()   # DB에 커밋 (저장)
    await db.refresh(db_product)  # DB에서 방금 생성된 ID 등을 다시 읽어옴
    return db_product

# 4. ID 목록으로 여러 상품 조회 (추천 API에서 사용)
async def get_products_by_ids(db: AsyncSession, product_ids: List[int]):
    if not product_ids:
        return []
        
    result = await db.execute(select(Product).filter(Product.id.in_(product_ids)))
    return result.scalars().all()