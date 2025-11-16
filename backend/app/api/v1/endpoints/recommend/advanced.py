# backend/app/api/v1/endpoints/recommend/advanced.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.schemas.product import Product
from app.models.product import Product as ProductModel
from app.crud import crud_recommend, crud_product
from .utils import reorder_products

router = APIRouter()


@router.get("/by-color/{product_id}", response_model=List[Product])
async def recommend_by_color(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """같은 카테고리, 다른 색상 추천"""
    print(f"\n🎨 상품 ID {product_id} - 색상별 추천")
    
    base_product_result = await db.execute(
        select(ProductModel).filter(ProductModel.id == product_id)
    )
    base_product = base_product_result.scalars().first()
    
    if not base_product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    similar_category_result = await db.execute(
        select(ProductModel).filter(
            ProductModel.category == base_product.category,
            ProductModel.color != base_product.color,
            ProductModel.id != product_id
        ).limit(5)
    )
    similar_products = similar_category_result.scalars().all()
    
    print(f"✅ {len(similar_products)}개 발견")
    
    return [Product.from_orm(p) for p in similar_products]


@router.get("/by-price-range/{product_id}", response_model=List[Product])
async def recommend_by_price(
    product_id: int,
    price_diff: int = 30000,
    db: AsyncSession = Depends(get_db)
):
    """비슷한 가격대 추천"""
    print(f"\n💰 상품 ID {product_id} - 가격대별 추천 (±{price_diff:,}원)")
    
    base_product_result = await db.execute(
        select(ProductModel).filter(ProductModel.id == product_id)
    )
    base_product = base_product_result.scalars().first()
    
    if not base_product or not base_product.price:
        raise HTTPException(status_code=404, detail="상품 또는 가격 정보 없음")
    
    min_price = base_product.price - price_diff
    max_price = base_product.price + price_diff
    
    similar_price_result = await db.execute(
        select(ProductModel).filter(
            ProductModel.price >= min_price,
            ProductModel.price <= max_price,
            ProductModel.id != product_id
        ).limit(5)
    )
    
    products = similar_price_result.scalars().all()
    print(f"✅ {len(products)}개 발견")
    
    return [Product.from_orm(p) for p in products]


@router.get("/by-season", response_model=List[Product])
async def recommend_by_season(
    season: str,
    category: str = None,
    db: AsyncSession = Depends(get_db)
):
    """시즌별 추천"""
    print(f"\n🌸 시즌: {season}, 카테고리: {category or '전체'}")
    
    stmt = select(ProductModel).filter(ProductModel.season == season)
    
    if category:
        stmt = stmt.filter(ProductModel.category == category)
    
    result = await db.execute(stmt.limit(10))
    products = result.scalars().all()
    
    print(f"✅ {len(products)}개 발견")
    
    return [Product.from_orm(p) for p in products]


@router.get("/coordination/{product_id}", response_model=List[Product])
async def recommend_coordination(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """코디 추천 (상/하의 매칭)"""
    print(f"\n👔 상품 ID {product_id} - 코디 추천")
    
    base_product_result = await db.execute(
        select(ProductModel).filter(ProductModel.id == product_id)
    )
    base_product = base_product_result.scalars().first()
    
    if not base_product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    coordination_map = {
        "아우터": "팬츠",
        "팬츠": "아우터",
        "상의": "팬츠",
    }
    
    target_category = coordination_map.get(base_product.category)
    
    if not target_category:
        raise HTTPException(status_code=400, detail="코디 추천 불가능한 카테고리")
    
    other_category_result = await db.execute(
        select(ProductModel).filter(
            ProductModel.category == target_category
        ).limit(5)
    )
    
    products = other_category_result.scalars().all()
    print(f"✅ {len(products)}개 발견")
    
    return [Product.from_orm(p) for p in products]