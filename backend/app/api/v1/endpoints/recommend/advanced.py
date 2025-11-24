from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

# ★★★ products 모듈의 extract_filters 가져오기 (경로 확인 필수)
# 만약 순환 참조 에러가 난다면, extract_filters 로직만 따로 utils.py 등으로 빼는 것이 좋지만,
# 현재 구조상으로는 임포트 위치만 주의하면 됩니다.
from app.api.v1.endpoints.products import extract_filters 

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
    """같은 카테고리, 다른 색상 추천 (None 에러 방지)"""
    print(f"\n🎨 상품 ID {product_id} - 색상별 추천")
    
    base_product_result = await db.execute(
        select(ProductModel).filter(ProductModel.id == product_id)
    )
    base_product = base_product_result.scalars().first()
    
    if not base_product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    # ★ [안전장치] None 방지
    current_cat = base_product.category or ""
    current_color = base_product.color or ""
    
    if not current_cat:
        print("⚠️ 카테고리 정보 없음 -> 색상 추천 스킵")
        return []

    # 쿼리 작성
    query = select(ProductModel).filter(
        ProductModel.category == current_cat, # 같은 옷 종류
        ProductModel.id != product_id         # 자기 자신 제외
    )
    
    # 색상 정보가 있으면 '다른 색상'을 우선적으로 찾음
    if current_color:
        query = query.filter(ProductModel.color != current_color)
    
    similar_category_result = await db.execute(query.limit(5))
    similar_products = similar_category_result.scalars().all()
    
    print(f"✅ {len(similar_products)}개 발견")
    
    return [Product.from_orm(p) for p in similar_products]


@router.get("/by-price-range/{product_id}", response_model=List[Product])
async def recommend_by_price(
    product_id: int,
    price_diff: int = 30000,
    db: AsyncSession = Depends(get_db)
):
    """비슷한 가격대 추천 (성별 필터 적용 - 개선됨)"""
    print(f"\n💰 상품 ID {product_id} - 가격대별 추천 (±{price_diff:,}원)")
    
    base_product_result = await db.execute(
        select(ProductModel).filter(ProductModel.id == product_id)
    )
    base_product = base_product_result.scalars().first()
    
    if not base_product or not base_product.price:
        raise HTTPException(status_code=404, detail="상품 또는 가격 정보 없음")
    
    min_price = base_product.price - price_diff
    max_price = base_product.price + price_diff
    
    # ★ [성별 감지 개선] extract_filters 재사용
    product_info = f"{base_product.name} {base_product.description or ''}"
    filters = extract_filters(product_info)
    gender = filters.get('gender')
    
    print(f"🎯 감지된 성별: {gender}")
    
    # 기본 쿼리
    query = select(ProductModel).filter(
        ProductModel.price >= min_price,
        ProductModel.price <= max_price,
        ProductModel.id != product_id
    )
    
    # ★ [필터 적용] 네거티브 필터 방식
    if gender == "여성":
        query = query.filter(
            ~ProductModel.name.like("%남성%"), 
            ~ProductModel.name.like("%남자%"),
            ~ProductModel.name.like("%맨즈%")
        )
    elif gender == "남성":
        query = query.filter(
            ~ProductModel.name.like("%여성%"), 
            ~ProductModel.name.like("%여자%"),
            ~ProductModel.name.like("%우먼%"),
            ~ProductModel.name.like("%원피스%"),
            ~ProductModel.name.like("%스커트%")
        )
    
    query = query.limit(5)
    
    similar_price_result = await db.execute(query)
    products = similar_price_result.scalars().all()
    
    print(f"✅ {len(products)}개 발견 (성별 필터: {gender})")
    
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
    """코디 추천 (상/하의 매칭 - 로직 강화)"""
    print(f"\n👔 상품 ID {product_id} - 코디 추천")
    
    base_product_result = await db.execute(
        select(ProductModel).filter(ProductModel.id == product_id)
    )
    base_product = base_product_result.scalars().first()
    
    if not base_product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    # ★ [안전장치] None 방지
    cat = base_product.category or ""
    
    # ★ [매핑 확장] 코디 맵
    coordination_map = {
        # 상의류 -> 하의 추천
        "상의": "하의",
        "티셔츠": "바지",
        "맨투맨": "바지",
        "후드": "바지",
        "니트": "슬랙스",
        "셔츠": "슬랙스",
        "블라우스": "스커트",
        
        # 하의류 -> 상의 추천
        "하의": "상의",
        "바지": "맨투맨",
        "팬츠": "티셔츠",
        "슬랙스": "셔츠",
        "청바지": "티셔츠",
        "스커트": "블라우스",
        "치마": "니트",
        "레깅스": "티셔츠",
        
        # 아우터 -> 이너(상의) 추천
        "아우터": "상의",
        "자켓": "티셔츠",
        "코트": "니트",
        "패딩": "맨투맨",
        "가디건": "티셔츠",
        
        # 원피스 -> 아우터 추천
        "원피스": "가디건",
        "드레스": "자켓",
        
        # 기타 -> 상의 추천 (기본값)
        "신발": "바지",
        "모자": "맨투맨"
    }
    
    # 타겟 카테고리 결정
    if cat in coordination_map:
        target_category = coordination_map[cat]
    else:
        # 유추 로직
        if "바지" in cat or "팬츠" in cat or "스커트" in cat:
            target_category = "상의"
        else:
            target_category = "하의" # 기본값
            
    print(f"🎯 기준: {cat} -> 추천 목표: {target_category}")
    
    # 추천 쿼리 실행
    other_category_result = await db.execute(
        select(ProductModel).filter(
            (ProductModel.category == target_category) | 
            (ProductModel.category.like(f"%{target_category}%"))
        ).limit(5)
    )
    
    products = other_category_result.scalars().all()
    
    # ★ [안전장치] 추천할 게 없으면 랜덤 추천 (에러 방지)
    if not products:
        print("⚠️ 매칭되는 코디 상품이 없어서 대체 상품을 찾습니다.")
        fallback_query = select(ProductModel).filter(ProductModel.id != product_id).limit(5)
        products = (await db.execute(fallback_query)).scalars().all()

    print(f"✅ {len(products)}개 발견")
    
    return [Product.from_orm(p) for p in products]