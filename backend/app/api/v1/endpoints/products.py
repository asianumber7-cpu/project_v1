# backend/app/api/v1/endpoints/products.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from transformers import AutoProcessor, AutoModel
import torch
import torch.nn.functional as F

from app.db.database import get_db
from app.schemas.product import Product, ProductCreate
from app.crud import crud_product

router = APIRouter()

# --- AI 모델 로드 ---
MODEL_NAME = 'koclip/koclip-base-pt'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print("🔄 AI 모델 로딩 중...")
try:
    model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    print("✅ AI 모델 로딩 완료!")
except Exception as e:
    print(f"❌ AI 모델 로딩 실패: {e}")
    model = None
    processor = None

class SearchRequest(BaseModel):
    query: str

# ---------------------------------------------------------

def extract_filters(query: str) -> dict:
    """쿼리에서 성별, 계절 추출"""
    query_lower = query.lower()
    
    # 성별 감지
    gender = None
    if any(word in query_lower for word in ["여성", "여자", "우먼", "여", "여성꺼", "여자꺼"]):
        gender = "여성"
    elif any(word in query_lower for word in ["남성", "남자", "맨즈", "남", "남성꺼", "남자꺼"]):
        gender = "남성"
    
    # 계절 감지
    season = None
    if "겨울" in query_lower:
        season = "겨울"
    elif "여름" in query_lower:
        season = "여름"
    elif "봄" in query_lower:
        season = "봄"
    elif "가을" in query_lower:
        season = "가을"
    elif "사계절" in query_lower or "4계절" in query_lower:
        season = "사계절"
    
    return {
        "gender": gender,
        "season": season
    }


def extract_core_keywords(query: str, gender: str = None) -> list:
    """핵심 키워드만 추출 (불용어/조사 제거)"""
    # 불용어
    stopwords = {
        '을', '를', '이', '가', '은', '는', '의', '에', '와', '과',
        '입을', '할때', '때', '할', '추천', '추천해줘', '해줘', '좀',
        '에서', '입을만한', '입기', '좋은', '적합한', '어울리는',
        '입을옷', '옷', '꺼로', '것', '거', '남성꺼로', '여성꺼로', '남자꺼로', '여자꺼로'
    }
    
    # ★★★ 키워드 확장 사전 (부분 매칭용) ★★★
    keyword_patterns = {
        # 운동 관련
        "운동": ["레깅스", "쇼츠", "타이즈"],
        "트레이닝": ["레깅스", "쇼츠", "타이즈"],
        "헬스": ["레깅스", "쇼츠", "타이즈", "컴프레션"],
        "요가": ["레깅스"],
        "필라테스": ["레깅스"],
        "러닝": ["쇼츠", "레깅스"],
        "조깅": ["쇼츠", "레깅스"],
        "달리기": ["쇼츠", "레깅스"],
        
        # ★ 계절/날씨 (부분 매칭)
        "추": ["패딩", "롱패딩", "코트", "자켓"],  # 추워, 추운, 춥다, 추울때
        "얼어": ["패딩", "롱패딩", "코트", "자켓"],  # 얼어죽을, 얼어죽겠
        "겨울": ["패딩", "롱패딩", "코트", "자켓"],
        "더": ["쇼츠"],  # 더워, 더운, 덥다, 더워죽
        "더워": ["쇼츠"],  # 더워죽겠다, 더워죽을
        "여름": ["쇼츠"],
        "시원": ["쇼츠"],
        "따뜻": ["패딩", "롱패딩", "코트", "자켓"],
        "포근": ["패딩", "롱패딩", "코트", "자켓"],
        "땀": ["쇼츠"],
        
        # 아웃도어
        "등산": ["아노락", "자켓", "팬츠"],
        "캠핑": ["아노락", "자켓"],
        "아웃도어": ["아노락", "자켓", "팬츠"],
        
        # 성별 관련
        "여자": ["여성"],
        "남자": ["남성"],
        "여성": ["여성"],
        "남성": ["남성"],
        
        # 스타일
        "편한": ["맨투맨", "후드", "조거팬츠"],
        "캐주얼": ["맨투맨", "후드", "청바지"],
        "정장": ["셔츠", "블라우스", "슬랙스", "자켓"],
        
        # 상황별
        "비": ["아노락", "자켓"],
        "눈": ["패딩", "롱패딩"],
    }
    
    # ★★★ 용도별 (성별에 따라) ★★★
    if gender == "남성":
        keyword_patterns.update({
            "데이트": ["셔츠", "자켓", "슬랙스"],
            "소개팅": ["셔츠", "자켓", "슬랙스"],
            "출근": ["셔츠", "슬랙스", "자켓"],
            "면접": ["셔츠", "슬랙스", "자켓"],
        })
    elif gender == "여성":
        keyword_patterns.update({
            "데이트": ["원피스", "블라우스", "스커트"],
            "소개팅": ["원피스", "블라우스", "스커트"],
            "출근": ["블라우스", "스커트", "자켓"],
            "면접": ["블라우스", "스커트", "자켓"],
        })
    else:
        keyword_patterns.update({
            "데이트": ["셔츠", "자켓"],
            "소개팅": ["셔츠", "자켓"],
            "출근": ["셔츠", "자켓"],
            "면접": ["셔츠", "자켓"],
        })
    
    words = query.split()
    keywords = []
    
    for word in words:
        # 불용어 제거
        if word in stopwords or len(word) <= 1:
            continue
        
        # ★★★ 부분 매칭으로 확장 ★★★
        matched = False
        for pattern, expanded in keyword_patterns.items():
            if pattern in word:  # ← 부분 매칭
                keywords.extend(expanded)
                matched = True
                break
        
        if not matched:
            keywords.append(word)
    
    # 중복 제거
    return list(set(keywords))


# 1. 텍스트 검색 API
@router.post("/search", response_model=List[Product])
async def search_products(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    query = request.query
    clean_query = query.replace("추천해줘", "").replace("추천", "").strip()
    if not clean_query: 
        clean_query = query

    print(f"🔍 검색어: {query} -> {clean_query}")

    if not model or not processor:
        raise HTTPException(status_code=500, detail="AI Model not loaded")

    # 필터 추출
    filters = extract_filters(clean_query)
    print(f"🎯 필터: 성별={filters['gender']}, 계절={filters['season']}")

    # 텍스트 → 벡터
    inputs = processor(
        text=clean_query, 
        return_tensors="pt", 
        padding=True, 
        truncation=True,
        max_length=77
    ).to(DEVICE)
    
    text_features = model.get_text_features(**inputs)
    text_features = F.normalize(text_features, p=2, dim=1)
    query_vector = text_features[0].cpu().detach().numpy().tolist()

    # ★ gender 전달 (핵심!)
    core_keywords = extract_core_keywords(clean_query, gender=filters['gender'])
    print(f"🔑 추출된 키워드: {core_keywords}")
    
    # 쿼리 타입 분석
    if len(core_keywords) == 1 and core_keywords[0] in ["레깅스", "패딩", "자켓", "원피스", "스커트", "쇼츠"]:
        # 단일 카테고리 검색
        print(f"📌 카테고리 검색 모드")
        results = await crud_product.search_products_by_text_vector(
            db, 
            query_vector, 
            top_k=20,
            threshold=0.35,
            keywords=core_keywords,
            season_filter=filters['season'],
            gender_filter=filters['gender']
        )
    elif len(core_keywords) >= 1:
        # 복합 검색
        print(f"📌 복합 검색 모드")
        results = await crud_product.search_products_by_text_vector(
            db, 
            query_vector, 
            top_k=20,
            threshold=0.30,
            keywords=core_keywords,
            season_filter=filters['season'],
            gender_filter=filters['gender']
        )
    else:
        # 벡터 검색만
        print(f"📌 벡터 검색 모드")
        results = await crud_product.search_products_by_text_vector(
            db, 
            query_vector, 
            top_k=20,
            threshold=0.35,
            keywords=None,
            season_filter=filters['season'],
            gender_filter=filters['gender']
        )
    
    return results


# 2. 다른 색상 보기 API
@router.get("/{product_id}/colors", response_model=List[Product])
async def get_color_variations(
    product_id: int, 
    db: AsyncSession = Depends(get_db)
):
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