# backend/app/crud/crud_recommend.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.models.product_vector import ProductVector
from app.models.product import Product

# 1. 특정 상품의 벡터를 가져오는 함수
async def get_vector_by_product_id(db: AsyncSession, product_id: int):
    result = await db.execute(
        select(ProductVector).filter(ProductVector.product_id == product_id)
    )
    db_vector = result.scalars().first()
    
    if db_vector:
        return db_vector.vector  # [0.1, 0.2, ...]
    return None

# 2. 사이즈로 필터링된 벡터 목록을 가져오는 함수
async def get_filtered_vectors(db: AsyncSession, size: str | None = None):
    """
    size 필터가 있으면, 해당 사이즈 재고가 있는 상품의 벡터만 조회
    """
    
    # 1. ProductVector와 Product를 join (연결)
    stmt = select(ProductVector.product_id, ProductVector.vector).join(
        Product, Product.id == ProductVector.product_id
    )
    
    # 2. size 파라미터가 있으면, 필터(WHERE) 조건 추가
    if size:
        # Product.size_info JSON 컬럼에서 'size' 키를 찾음
        # 예: size="M" -> size_info['M']
        # (MySQL의 JSON_EXTRACT, JSON_KEYS와 유사한 SQLAlchemy 기능)
        stmt = stmt.filter(Product.size_info.op("->")(size).is_not(None))

    result = await db.execute(stmt)
    return result.all()


# 2. DB에 저장된 "모든" 상품의 벡터와 product_id를 가져오는 함수
async def get_all_vectors(db: AsyncSession):
    result = await db.execute(select(ProductVector.product_id, ProductVector.vector))
    
    # [(1, [0.1, ...]), (2, [0.5, ...]), ...]
    return result.all()

# 3. 코사인 유사도 계산 및 Top N 반환
def get_top_n_similar_products(target_vector, all_vectors_data, n=5):
    """
    target_vector: 기준이 되는 상품의 벡터 (1D array)
    all_vectors_data: (product_id, vector) 튜플의 리스트
    n: 상위 몇 개를 반환할지
    """
    
    # 비교를 위해 (product_id 리스트)와 (벡터 리스트)로 분리
    product_ids = [item[0] for item in all_vectors_data]
    vectors = [item[1] for item in all_vectors_data]
    
    # scikit-learn은 2D 배열을 기대하므로, 1D 벡터를 2D로 변환
    target_vector_2d = np.array(target_vector).reshape(1, -1)
    
    # 모든 벡터 리스트도 2D 배열로 변환
    all_vectors_2d = np.array(vectors)
    
    # (★핵심★) 코사인 유사도 계산
    # 결과: [[0.5, 0.9, 0.1, ...]] 형태의 2D 배열
    similarities = cosine_similarity(target_vector_2d, all_vectors_2d)
    
    # 유사도 점수와 product_id를 튜플로 묶음: (product_id, similarity)
    # similarities[0]을 사용해 1D 배열로 만듦
    paired_scores = list(zip(product_ids, similarities[0]))
    
    # 유사도 점수(x[1])를 기준으로 내림차순(reverse=True) 정렬
    sorted_scores = sorted(paired_scores, key=lambda x: x[1], reverse=True)
    
    # 상위 N+1개를 반환 (자기 자신(유사도 1.0)을 제외하기 위함)
    # (결과 예: [(1, 1.0), (5, 0.95), (3, 0.89), ...])
    top_n_plus_one = sorted_scores[0 : n + 1]
    
    return top_n_plus_one