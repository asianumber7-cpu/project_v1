# backend/app/api/v1/endpoints/recommend/__init__.py

from fastapi import APIRouter
from . import base, advanced

router = APIRouter()

# 기본 추천 라우터
router.include_router(base.router, tags=["기본 추천"])

# 고급 추천 라우터
router.include_router(advanced.router, tags=["고급 추천"])