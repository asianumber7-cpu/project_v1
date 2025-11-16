# backend/app/api/v1/api.py

from fastapi import APIRouter
from app.api.v1.endpoints import users, products, recommend

api_router = APIRouter()

# 2. users 라우터 포함
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 3. products 라우터 포함
api_router.include_router(products.router, prefix="/products", tags=["products"])

# 3. recommend 라우터 포함 
api_router.include_router(recommend.router, prefix="/recommend", tags=["recommend"])