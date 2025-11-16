# backend/app/api/v1/endpoints/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.schemas.product import Product, ProductCreate
from app.crud import crud_product

router = APIRouter()

# 1. 상품 생성 API
@router.post("/", response_model=Product)
async def create_new_product(
    product: ProductCreate, 
    db: AsyncSession = Depends(get_db)
):
    # (참고) 실제로는 이 API는 관리자만 호출할 수 있도록
    # (users.py의 로그인 API처럼) 인증(Auth) 로직이 추가되어야 합니다.
    # 지금은 MVP를 위해 누구나 생성 가능하게 열어둡니다.
    return await crud_product.create_product(db=db, product=product)

# 2. 상품 목록 조회 API
@router.get("/", response_model=List[Product])
async def read_all_products(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    products = await crud_product.get_products(db, skip=skip, limit=limit)
    return products

# 3. 특정 상품 1개 조회 API
@router.get("/{product_id}", response_model=Product)
async def read_single_product(
    product_id: int, 
    db: AsyncSession = Depends(get_db)
):
    db_product = await crud_product.get_product(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product