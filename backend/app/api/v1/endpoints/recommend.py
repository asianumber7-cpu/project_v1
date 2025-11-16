# backend/app/api/v1/endpoints/recommend.py (★최종 수정본★)

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sentence_transformers import SentenceTransformer
import io
from PIL import Image

from app.db.database import get_db
from app.schemas.product import Product
from app.crud import crud_recommend, crud_product

# --- 모델 로드 (기존과 동일) ---
TEXT_CLIP_MODEL = 'sentence-transformers/clip-ViT-B-32-multilingual-v1'
IMAGE_CLIP_MODEL = 'clip-ViT-B-32'
logger = None 

try:
    text_model = SentenceTransformer(TEXT_CLIP_MODEL)
    print("텍스트 CLIP 모델 로드 성공.")
    image_model = SentenceTransformer(IMAGE_CLIP_MODEL)
    print("이미지 CLIP 모델 로드 성공.")
except Exception as e:
    print(f"CLIP 모델 로드 실패: {e}")
    text_model = None
    image_model = None

router = APIRouter()

# --- (★공통 헬퍼 함수 추가★) ---
# AI가 정한 순서(ids)대로 DB에서 온 리스트(products)를 재정렬합니다.
def reorder_products(products: List[Product], product_ids: List[int]) -> List[Product]:
    # 1. product.id를 키로 하는 딕셔너리(해시맵)를 만들어 빠른 조회를 지원
    product_map = {product.id: product for product in products}
    
    # 2. AI가 정한 id 순서대로 맵에서 product를 꺼내 새 리스트 생성
    # (id가 맵에 없는 경우는 무시)
    ordered_products = [product_map[pid] for pid in product_ids if pid in product_map]
    return ordered_products
# ---


# (아이디어 1) 상품 ID 기반 유사 상품 추천 API
@router.get("/by-product/{product_id}", response_model=List[Product])
async def recommend_similar_products(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    target_vector = await crud_recommend.get_vector_by_product_id(db, product_id)
    if not target_vector:
        raise HTTPException(status_code=404, detail="기준 상품의 AI 벡터를 찾을 수 없습니다.")

    all_vectors_data = await crud_recommend.get_all_vectors(db)
    if not all_vectors_data:
        raise HTTPException(status_code=404, detail="비교할 상품 벡터가 DB에 없습니다.")

    top_n_results = crud_recommend.get_top_n_similar_products(
        target_vector, 
        all_vectors_data, 
        n=5
    )

    recommended_product_ids = []
    for pid, score in top_n_results:
        if pid != product_id and pid not in recommended_product_ids:
            recommended_product_ids.append(pid)
        if len(recommended_product_ids) >= 5:
            break
            
    # [버그 수정] ID로 조회 (DB가 순서를 섞음)
    unordered_products = await crud_product.get_products_by_ids(db, product_ids=recommended_product_ids)
    
    # [★해결★] AI 순서대로 재정렬
    ordered_products = reorder_products(unordered_products, recommended_product_ids)

    return ordered_products


# (아이디어 2: 텍스트 검색 + 아이디어 3: 사이즈 필터)
@router.get("/by-text", response_model=List[Product])
async def recommend_by_text_search(
    query: str,
    size: str | None = None,
    db: AsyncSession = Depends(get_db)
):
    if not text_model:
        raise HTTPException(status_code=503, detail="AI 모델이 로드되지 않았습니다.")
        
    target_vector = text_model.encode(query).tolist()

    all_vectors_data = await crud_recommend.get_filtered_vectors(db, size=size)
    
    if not all_vectors_data:
        raise HTTPException(
            status_code=404, 
            detail=f"'{size}' 사이즈에 해당하는 상품 벡터가 DB에 없습니다." if size else "비교할 상품 벡터가 DB에 없습니다."
        )

    top_n_results = crud_recommend.get_top_n_similar_products(
        target_vector, 
        all_vectors_data, 
        n=5
    )

    recommended_product_ids = [pid for pid, score in top_n_results[:5]]

    # [버그 수정] ID로 조회 (DB가 순서를 섞음)
    unordered_products = await crud_product.get_products_by_ids(db, product_ids=recommended_product_ids)
    
    # [★해결★] AI 순서대로 재정렬
    ordered_products = reorder_products(unordered_products, recommended_product_ids)

    return ordered_products


# (아이디어 4) 사용자 이미지 업로드 기반 추천 API
@router.post("/by-image-upload", response_model=List[Product])
async def recommend_by_image_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    if not image_model:
        raise HTTPException(status_code=503, detail="이미지 AI 모델이 로드되지 않았습니다.")
        
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"이미지 파일을 읽는 데 실패했습니다: {e}")
    finally:
        await file.close()

    try:
        image_rgb = image.convert("RGB")
        target_vector = image_model.encode(image_rgb).tolist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 벡터화에 실패했습니다: {e}")

    all_vectors_data = await crud_recommend.get_all_vectors(db)
    if not all_vectors_data:
        raise HTTPException(status_code=404, detail="비교할 상품 벡터가 DB에 없습니다.")

    top_n_results = crud_recommend.get_top_n_similar_products(
        target_vector, 
        all_vectors_data, 
        n=5
    )

    recommended_product_ids = [pid for pid, score in top_n_results[:5]]

    # [버그 수정] ID로 조회 (DB가 순서를 섞음)
    unordered_products = await crud_product.get_products_by_ids(db, product_ids=recommended_product_ids)
    
    # [★해결★] AI 순서대로 재정렬
    ordered_products = reorder_products(unordered_products, recommended_product_ids)

    return ordered_products