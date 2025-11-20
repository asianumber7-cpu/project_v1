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
    threshold: float = 0.65,
    keywords: list = None,  # ← 수정: str → list
    season_filter: str = None
):
    """
    텍스트 쿼리 벡터로 상품의 text_vector와 비교하여 검색
    사용처: "패딩", "원피스" 같은 텍스트 검색
    keywords: 모든 키워드가 상품명에 포함되어야 함 (AND 조건)
    """
    result = await db.execute(select(Product))
    products = result.scalars().all()

    scored_products = []
    
    for product in products:
        if not product.text_vector:
            continue

        # ★ 계절 필터링 (추가)
        if season_filter and product.season:
            # 해당 계절이거나 사계절 상품만 통과
            if season_filter not in product.season and "사계절" not in product.season:
                continue
        
        # ★ 키워드 필터링 (모든 키워드 AND 조건)
        if keywords:
            product_name_lower = product.name.lower()
            # 모든 키워드가 상품명에 있는지 확인
            if not all(kw.lower() in product_name_lower for kw in keywords):
                continue
            
        score = cosine_similarity(query_vector, product.text_vector)
        
        if score >= threshold:
            scored_products.append((product, score))

           

    # 점수 높은 순 정렬
    scored_products.sort(key=lambda x: x[1], reverse=True)
    
    # 상위 K개
    final_results = scored_products[:top_k]

    # 디버깅 출력
    print("\n" + "="*50)
    print(f"🔍 텍스트 검색 (키워드: {keywords}, 커트라인: {threshold})")
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