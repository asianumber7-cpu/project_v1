# backend/app/api/v1/endpoints/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

# AI 모델 관련
from transformers import AutoProcessor, AutoModel
import torch
import torch.nn.functional as F

from app.db.database import get_db
from app.schemas.product import Product, ProductCreate
from app.crud import crud_product

router = APIRouter()

# --- AI 모델 로드 (서버 시작 시 1회만 실행) ---
MODEL_NAME = 'koclip/koclip-base-pt'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print("🔄 AI 모델 로딩 중... (최대 30초 소요)")
try:
    model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    print("✅ AI 모델 로딩 완료!")
except Exception as e:
    print(f"❌ AI 모델 로딩 실패: {e}")
    model = None
    processor = None

# 요청 스키마
class SearchRequest(BaseModel):
    query: str

# ---------------------------------------------------------
# API 엔드포인트
# ---------------------------------------------------------

# 1. 텍스트 검색 API (메인 검색)
@router.post("/search", response_model=List[Product])
async def search_products(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    텍스트 쿼리로 상품 검색
    예: "패딩", "원피스", "검은색 스커트"
    """
    query = request.query
    
    # 검색어 정제 (불필요한 단어 제거)
    clean_query = query.replace("추천해줘", "").replace("추천", "").strip()
    if not clean_query: 
        clean_query = query

    print(f"🔍 검색어: {query} -> {clean_query}")

    if not model or not processor:
        raise HTTPException(status_code=500, detail="AI Model not loaded")

    # 텍스트 → 벡터 변환
    inputs = processor(
        text=clean_query, 
        return_tensors="pt", 
        padding=True, 
        truncation=True,
        max_length=77
    ).to(DEVICE)
    
    text_features = model.get_text_features(**inputs)
    
    # 정규화 (필수!)
    text_features = F.normalize(text_features, p=2, dim=1)
    query_vector = text_features[0].cpu().detach().numpy().tolist()

    season = None
    if "겨울" in clean_query:
        season = "겨울"
    elif "여름" in clean_query:
        season = "여름"
    elif "봄" in clean_query:
        season = "봄"
    elif "가을" in clean_query:
        season = "가을"

    query_words = clean_query.split()

    if len(query_words) <= 2:
        stopwords = ['을', '를', '이', '가', '은', '는', '의', '에']
        keywords = [w for w in query_words if w not in stopwords and len(w) > 1]
        if not keywords:
            keywords = None
        
        results = await crud_product.search_products_by_text_vector(
            db, 
            query_vector, 
            top_k=20,
            threshold=0.65,
            keywords=keywords,
            season_filter=season
        )
    
    # 2) 긴 쿼리 (3단어 이상): 키워드 필터 제거 (의미 검색 우선)
    else:
        results = await crud_product.search_products_by_text_vector(
            db, 
            query_vector, 
            top_k=20,
            threshold=0.55,  # threshold 낮춤 (더 많은 결과)
            keywords=None,  # 키워드 필터 사용 안 함
            season_filter=season
        )
    
    return results


# 2. 다른 색상 보기 API
@router.get("/{product_id}/colors", response_model=List[Product])
async def get_color_variations(
    product_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    동일 디자인의 다른 색상 상품 찾기
    """
    current_product = await crud_product.get_product(db, product_id)
    if not current_product:
        raise HTTPException(status_code=404, detail="Product not found")

    variations = await crud_product.get_similar_products_by_name(
        db, 
        current_product.name, 
        product_id
    )
    return variations


# 3. 상품 생성 API
@router.post("/", response_model=Product)
async def create_new_product(
    product: ProductCreate, 
    db: AsyncSession = Depends(get_db)
):
    return await crud_product.create_product(db=db, product=product)


# 4. 상품 목록 조회 API
@router.get("/", response_model=List[Product])
async def read_all_products(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    products = await crud_product.get_products(db, skip=skip, limit=limit)
    return products


# 5. 특정 상품 조회 API
@router.get("/{product_id}", response_model=Product)
async def read_single_product(
    product_id: int, 
    db: AsyncSession = Depends(get_db)
):
    db_product = await crud_product.get_product(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product