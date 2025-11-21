# backend/app/crud/crud_product.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from app.models.product import Product
from app.models.product_vector import ProductVector
import numpy as np

# 1. 상품 조회
async def get_product(db: AsyncSession, product_id: int):
    result = await db.execute(select(Product).filter(Product.id == product_id))
    return result.scalars().first()

# 2. 상품 목록 조회
async def get_products(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(Product).offset(skip).limit(limit))
    return result.scalars().all()

# 3. 상품 생성
async def create_product(db: AsyncSession, product):
    db_product = Product(
        name=product.name,
        description=product.description,
        image_url=product.image_url,
        size_info=product.size_info,
        price=product.price,
        brand=product.brand,
        color=product.color,
        season=product.season
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

# 4. ID 목록 조회
async def get_products_by_ids(db: AsyncSession, product_ids: List[int]):
    if not product_ids:
        return []
    result = await db.execute(select(Product).filter(Product.id.in_(product_ids)))
    return result.scalars().all()

# --- AI 벡터 로직 ---

def cosine_similarity(v1, v2):
    """코사인 유사도 계산"""
    dot_product = np.dot(v1, v2)
    norm_a = np.linalg.norm(v1)
    norm_b = np.linalg.norm(v2)
    if norm_a == 0 or norm_b == 0:
        return 0
    return dot_product / (norm_a * norm_b)

# 5. 텍스트 벡터로 검색 (텍스트 쿼리용)
async def search_products_by_text_vector(
    db: AsyncSession, 
    query_vector: list, 
    top_k: int = 10, 
    threshold: float = 0.50,
    keywords: list = None,
    season_filter: str = None,
    gender_filter: str = None
):
    """텍스트 쿼리 벡터로 검색"""
    result = await db.execute(select(Product))
    products = result.scalars().all()

    # 여성 전용 아이템
    female_only_items = {"원피스", "블라우스", "스커트", "치마"}
    
    sports_keywords = {"레깅스", "쇼츠", "타이즈", "컴프레션"}
    has_sports_keyword = keywords and (sports_keywords & set(kw.lower() for kw in keywords))
    
    # 계절/날씨 키워드 감지
    hot_keywords = {"쇼츠"}  # 더울 때 키워드
    cold_keywords = {"패딩", "롱패딩", "코트"}  # 추울 때 키워드
    
    is_hot_query = keywords and any(kw in hot_keywords for kw in keywords)
    is_cold_query = keywords and any(kw in cold_keywords for kw in keywords)
    
    scored_products = []
    
    for product in products:
        if not product.text_vector:
            continue
        
        product_text = f"{product.name} {product.description or ''}".lower()
        
        # 계절 모순 필터링 
        if is_hot_query:
            # 더운 날씨 검색 시 겨울 아이템 제외
            if any(word in product_text for word in ["겨울", "윈터", "기모", "플리스", "패딩", "롱패딩", "울", "코듀로이"]):
                continue
        
        if is_cold_query:
            # 추운 날씨 검색 시 여름 아이템 제외
            if any(word in product_text for word in ["여름", "썸머", "비치", "쿨링", "메쉬"]):
                continue
        
        # 남성 필터 시 여성 전용 아이템 제외
        if gender_filter == "남성":
            if any(item in product_text for item in female_only_items):
                continue
        
        # 성별 필터
        if gender_filter:
            if gender_filter == "여성":
                has_female = "여성" in product.name or "여자" in product.name
                is_neutral_sports = has_sports_keyword and any(kw in product_text for kw in sports_keywords)
                is_likely_female = any(word in product_text for word in ["하이웨이스트", "요가", "필라테스"])
                
                if not (has_female or is_neutral_sports or is_likely_female):
                    if "남성" in product.name or "남자" in product.name:
                        continue
                        
            elif gender_filter == "남성":
                has_male = "남성" in product.name or "남자" in product.name
                is_neutral_sports = has_sports_keyword and any(kw in product_text for kw in sports_keywords)
                is_likely_male = any(word in product_text for word in ["컴프레션", "퍼포먼스", "머슬핏"])
                
                if not (has_male or (is_neutral_sports and not ("하이웨이스트" in product_text or "요가" in product_text)) or is_likely_male):
                    if "여성" in product.name or "여자" in product.name:
                        continue
        
        # 계절 필터
        if season_filter and product.season:
            if season_filter not in product.season and "사계절" not in product.season:
                continue
        
        # 키워드 필터
        if keywords:
            if not any(kw.lower() in product_text for kw in keywords):
                continue
        
        # 벡터 점수 계산
        score = cosine_similarity(query_vector, product.text_vector)
        
        # 운동복 부스트
        is_sports_product = False
        if has_sports_keyword:
            product_text_lower = f"{product.name} {product.description or ''}".lower()
            is_sports_product = any(sport_kw in product_text_lower for sport_kw in sports_keywords)
            
            if is_sports_product:
                score = score * 5.0
                print(f"  🏃 운동복 부스트: {product.name} ({score:.4f})")
        
        effective_threshold = threshold * 0.2 if is_sports_product else threshold
        
        if score >= effective_threshold:
            scored_products.append((product, score))

    scored_products.sort(key=lambda x: x[1], reverse=True)
    final_results = scored_products[:top_k]

    print("\n" + "="*50)
    print(f"🔍 텍스트 검색 (키워드: {keywords}, 성별: {gender_filter}, 계절: {season_filter}, 커트라인: {threshold})")
    if not final_results:
        print("❌ 조건에 맞는 상품이 없습니다.")
    else:
        for prod, score in final_results:
            print(f"✅ [점수: {score:.4f}] {prod.name}")
    print("="*50 + "\n")

    return [item[0] for item in final_results]

# 6. 이미지 벡터로 검색 (이미지 업로드용)
async def search_products_by_image_vector(
    db: AsyncSession, 
    query_vector: list, 
    top_k: int = 10, 
    threshold: float = 0.65
):
    """
    이미지 쿼리 벡터로 product_vectors(이미지 벡터)와 비교하여 검색
    사용처: 사용자가 이미지를 업로드했을 때
    """
    result = await db.execute(
        select(Product, ProductVector)
        .join(ProductVector, Product.id == ProductVector.product_id)
    )
    rows = result.all()

    scored_products = []
    
    for product, product_vector in rows:
        if not product_vector.vector:
            continue
            
        score = cosine_similarity(query_vector, product_vector.vector)
        
        if score >= threshold:
            scored_products.append((product, score))

    scored_products.sort(key=lambda x: x[1], reverse=True)
    final_results = scored_products[:top_k]

    print("\n" + "="*50)
    print(f"🖼️ 이미지 검색 결과 (커트라인: {threshold})")
    if not final_results:
        print("❌ 조건에 맞는 상품이 없습니다.")
    else:
        for prod, score in final_results:
            print(f"✅ [점수: {score:.4f}] {prod.name}")
    print("="*50 + "\n")

    return [item[0] for item in final_results]

# 7. 같은 디자인 다른 색상 찾기
async def get_similar_products_by_name(db: AsyncSession, product_name: str, current_id: int):
    """
    상품명 기반으로 유사 상품 찾기 (색상 변형 찾기용)
    """
    keywords = product_name.split()
    if len(keywords) >= 2:
        search_keyword = f"{keywords[0]} {keywords[1]}"
    else:
        search_keyword = keywords[0]

    result = await db.execute(
        select(Product)
        .filter(Product.name.like(f"%{search_keyword}%"))
        .filter(Product.id != current_id)
        .limit(5)
    )
    return result.scalars().all()