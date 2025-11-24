# backend/app/crud/crud_product.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_  # ★ [추가] SQL 필터링을 위해 필요
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


# 5. 텍스트 벡터로 검색
async def search_products_by_text_vector(
    db: AsyncSession, 
    query_vector: list, 
    top_k: int = 10, 
    threshold: float = 0.20,  
    keywords: list = None,
    season_filter: str = None,
    gender_filter: str = None
):
    stmt = select(Product, ProductVector).join(ProductVector, Product.id == ProductVector.product_id)
    
    # 1. 네거티브 필터 
    if gender_filter:
        if gender_filter == "남성":
            
            stmt = stmt.filter(
                ~Product.name.like("%여성%"), 
                ~Product.name.like("%여자%"),
                ~Product.name.like("%우먼%"),
                ~Product.description.like("%여성%"), # 설명도 검사
                ~Product.description.like("%여자%"),
                ~Product.name.like("%원피스%"),
                ~Product.name.like("%스커트%"),
                ~Product.name.like("%블라우스%"),
                ~Product.name.like("%레깅스%"),
                ~Product.name.like("%브라탑%"),
                ~Product.name.like("%크롭%"),
                ~Product.name.like("%캐미솔%"),
                ~Product.name.like("%슬립%")
            )
        elif gender_filter == "여성":
            stmt = stmt.filter(
                ~Product.name.like("%남성%"), 
                ~Product.name.like("%남자%"),
                ~Product.name.like("%맨즈%")
            )

    # 2. 계절 필터 (네거티브만 유지)
    if season_filter:
        if season_filter == "겨울":
            stmt = stmt.filter(
                ~Product.name.like("%반팔%"),
                ~Product.name.like("%쿨링%"),
                ~Product.name.like("%린넨%"),
                ~Product.season.like("%여름%")
            )
        elif season_filter == "여름":
            stmt = stmt.filter(
                ~Product.name.like("%기모%"),
                ~Product.name.like("%패딩%"),
                ~Product.season.like("%겨울%")
            )

    result = await db.execute(stmt)
    rows = result.all()

    scored_products = []
    
    # 색상 필터용 리스트 (하지만 강제로 거르진 않을 겁니다)
    COLOR_KEYWORDS = {"빨강", "레드", "버건디", "초록", "그린", "블루", "검정", "화이트"}
    query_colors = set(keywords) & COLOR_KEYWORDS if keywords else set()

    for product, prod_vec in rows:
        if not product.text_vector or not prod_vec.vector:
            continue

        product_text = f"{product.name} {product.description or ''} {product.color or ''}".lower()
        
        # --- 점수 계산 (기본) ---
        text_score = cosine_similarity(query_vector, product.text_vector)
        image_score = cosine_similarity(query_vector, prod_vec.vector)
        
        # 기본 점수 (이미지 60% + 텍스트 40%)
        final_score = (text_score * 0.4) + (image_score * 0.6)
        
        # --- ★★★ [핵심] 보너스 점수 시스템 (Bonus) ★★★ ---
        # 강제로 탈락(continue)시키는 대신, 점수를 더해줍니다.
        
        bonus = 0.0
        
        # 1. 색상 보너스 
        if query_colors:
            for color_kw in query_colors:
                if color_kw in product_text:
                    bonus += 0.1
                    break 
        
        # 2. 키워드 보너스 
        
        if keywords:
            for kw in keywords:
                
                if kw in product.name:
                    bonus += 0.15
                
                elif kw in product.description:
                    bonus += 0.05
            
            
            if bonus > 0.4: 
                bonus = 0.4
                

        # 3. TPO별 감점 로직 (여기가 핵심!)
        # 키워드에 '집', '잠옷', '파자마', '홈웨어' 등이 있는데
        # 상품명에 '데님', '레더', '패딩', '코트', '자켓'이 있으면 점수 대폭 깎기
        
        home_keywords = {'집', '잠옷', '파자마', '홈웨어', '방구석', '편한', '휴식', '수면'}
        outdoor_materials = {'데님', '청바지', '레더', '가죽', '패딩', '코트', '자켓', '블레이저', '파카', '야상', '슬랙스', '정장'}
        
        # 사용자가 '집' 관련 검색을 했는지 확인
        is_home_search = bool(set(keywords) & home_keywords) if keywords else False
        
        if is_home_search:
            # 상품명이나 설명에 외출용 소재가 있으면 감점
            for bad_word in outdoor_materials:
                if bad_word in product_text:
                    bonus -= 0.3  # 가산점보다 더 큰 감점 (순위권 밖으로 밀어냄)
                    # print(f"  📉 [집] 외출복 감점: {product.name} (-0.3)")
                    break

        # 3. TPO별 감점 로직 (상황에 맞지 않는 옷 쳐내기)
        
        # [A] 집/휴식 모드 (기존 로직 유지 및 보강)
        home_keywords = {'집', '방구석', '편한', '휴식'}
        outdoor_materials = {'데님', '청바지', '레더', '가죽', '패딩', '코트', '자켓', '블레이저', '파카', '야상', '슬랙스', '정장', '부츠', '구두'}
        
        is_home_search = bool(set(keywords) & home_keywords) if keywords else False
        
        if is_home_search:
            for bad_word in outdoor_materials:
                if bad_word in product_text:
                    bonus -= 0.3 
                    break

        # [B] ★★★ 수면/취침 모드 (초강력 버전) ★★★
        sleep_keywords = {'잠', '잘때', '수면', '파자마', '잠옷', '꿀잠', '자려'}
        is_sleep_search = bool(set(keywords) & sleep_keywords) if keywords else False
        
        if is_sleep_search:
            # 1. 금지어 리스트 (맨투맨, 요가 추가)
            sleep_ban_list = {
                '레깅스', '타이즈', '컴프레션', '요가', # 운동복 제외
                '윈드브레이커', '아노락', '바람막이', '나일론', 
                '스커트', '원피스', 
                '후드', '모자', # 모자 달린 거 잘 때 불편함
                '청바지', '데님', '슬랙스', '셔츠', '자켓', '코트', '패딩',
                '맨투맨', '트레이닝' # 맨투맨도 잘 때는 좀 두꺼워서 제외 (취향차이 있겠지만 꿀잠용은 아님)
            }
            
            for bad_word in sleep_ban_list:
                # 예외: "잠옷 원피스"는 허용
                if bad_word in product_text:
                    if bad_word == '원피스' and ('잠옷' in product_text or '파자마' in product_text):
                        continue 
                    
                    bonus -= 0.5 # 금지어 있으면 광탈
                    break
            
            # 2. ★★★ [핵심 추가] 진짜 잠옷 아니면 감점 ★★★
            # 상품명/설명에 "잠옷, 파자마, 수면, 홈웨어" 중 하나도 없으면 점수 깎음
            real_sleepwear_words = ['잠옷', '파자마', '수면', '홈웨어']
            is_real_sleepwear = any(word in product_text for word in real_sleepwear_words)
            
            if not is_real_sleepwear:
                bonus -= 0.3  # 잠옷이라고 안 써져 있으면 감점 (맨투맨 등이 여기서 또 걸러짐)

        final_score += bonus        
        
        # 문턱값 통과
        if final_score >= threshold:
            scored_products.append((product, final_score))

    scored_products.sort(key=lambda x: x[1], reverse=True)
    final_results = scored_products[:top_k]

    print(f"\n🔍 [스마트 AI 검색] 키워드:{keywords}, 보너스적용됨")
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