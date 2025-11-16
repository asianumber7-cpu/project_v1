# backend/app/crud/crud_recommend.py (★Text Vector 함수 추가★)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.models.product_vector import ProductVector
from app.models.product import Product # (★추가★)

# 1. (이미지) 특정 상품의 '이미지 벡터'
async def get_vector_by_product_id(db: AsyncSession, product_id: int):
    result = await db.execute(
        select(ProductVector).filter(ProductVector.product_id == product_id)
    )
    db_vector = result.scalars().first()
    
    if db_vector:
        return db_vector.vector
    return None

# 2. (이미지) '모든' 상품의 '이미지 벡터'
async def get_all_vectors(db: AsyncSession):
    result = await db.execute(select(ProductVector.product_id, ProductVector.vector))
    return result.all()

# 3. (★새 함수★) (텍스트) '모든' 상품의 '텍스트 벡터' (size 필터 포함)
async def get_all_text_vectors(db: AsyncSession, size: str | None = None):
    """
    Product 테이블에서 'text_vector'를 조회합니다.
    """
    
    # (★수정★) Product 테이블에서 product.id와 product.text_vector를 조회
    stmt = select(Product.id, Product.text_vector).filter(Product.text_vector != None)
    
    # size 파라미터가 있으면, 필터(WHERE) 조건 추가
    if size:
        # Product.size_info JSON 컬럼에서 'size' 키를 찾음
        stmt = stmt.filter(Product.size_info.op("->")(size).is_not(None))

    result = await db.execute(stmt)
    return result.all()


# (참고: 이 함수는 get_filtered_vectors를 대체합니다. 
#  get_filtered_vectors는 이제 사용되지 않습니다.)
async def get_filtered_vectors(db: AsyncSession, size: str | None = None):
    stmt = select(ProductVector.product_id, ProductVector.vector).join(
        Product, Product.id == ProductVector.product_id
    )
    if size:
        stmt = stmt.filter(Product.size_info.op("->")(size).is_not(None))
    result = await db.execute(stmt)
    return result.all()


# 4. (공통) 코사인 유사도 계산
def get_top_n_similar_products(target_vector, all_vectors_data, n=5):
    
    product_ids = [item[0] for item in all_vectors_data]
    vectors = [item[1] for item in all_vectors_data]
    
    if not vectors: # 혹시 벡터가 비어있으면 빈 리스트 반환
        return []
        
    target_vector_2d = np.array(target_vector).reshape(1, -1)
    all_vectors_2d = np.array(vectors)
    
    similarities = cosine_similarity(target_vector_2d, all_vectors_2d)
    
    paired_scores = list(zip(product_ids, similarities[0]))
    
    sorted_scores = sorted(paired_scores, key=lambda x: x[1], reverse=True)
    
    # 상위 N+1개를 반환 (유사도 비교 대상에 자기 자신이 포함될 수 있으므로)
    top_n_plus_one = sorted_scores[0 : n + 1]
    
    return top_n_plus_one