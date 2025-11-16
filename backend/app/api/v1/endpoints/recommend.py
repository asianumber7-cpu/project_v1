# backend/app/api/v1/endpoints/recommend.py (★ 하이브리드 검색 완전판 ★)

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from transformers import VisionTextDualEncoderModel, AutoTokenizer, AutoImageProcessor
import torch
import io
from PIL import Image

from app.db.database import get_db
from app.schemas.product import Product
from app.crud import crud_recommend, crud_product

# ★ KoCLIP 올바른 설정 ★
MODEL_NAME = 'koclip/koclip-base-pt'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

koclip_model = None
koclip_tokenizer = None
koclip_image_processor = None

try:
    print("KoCLIP 모델 로딩 시작...")
    koclip_model = VisionTextDualEncoderModel.from_pretrained(MODEL_NAME).to(DEVICE)
    koclip_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    koclip_image_processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
    koclip_model.eval()
    
    print(f"KoCLIP 모델 로드 완료! (Device: {DEVICE})")
except Exception as e:
    print(f"KoCLIP 모델 로드 실패: {e}")

router = APIRouter()


# ========================================
# ★ 키워드 확장 사전 ★
# ========================================
KEYWORD_EXPANSIONS = {
    "무스탕": "무스탕 자켓 스웨이드 양털 가죽",
    "청바지": "청바지 데님 진 pants",
    "데님": "데님 청바지 진 denim",
    "진": "진 청바지 데님 jeans",
    "후드": "후드 후드티 스웨트 hoodie",
    "트레이닝": "트레이닝 조거 팬츠 운동복",
    "조거": "조거 트레이닝 팬츠 운동복",
}


def expand_query(query: str) -> str:
    """검색 쿼리를 확장합니다."""
    query_lower = query.strip().lower()
    
    # 정확히 일치하는 키워드가 있으면 확장
    for key, expanded in KEYWORD_EXPANSIONS.items():
        if key in query_lower:
            return expanded
    
    return query


def calculate_keyword_score(query: str, product_name: str, product_description: str) -> float:
    """
    키워드 매칭 점수 계산 (0.0 ~ 1.0)
    쿼리에 포함된 단어가 상품명/설명에 있으면 높은 점수
    """
    query_lower = query.lower().strip()
    product_text = f"{product_name} {product_description}".lower()
    
    # 1. 정확히 일치하는 경우
    if query_lower in product_text:
        return 1.0
    
    # 2. 쿼리의 각 단어가 포함되어 있는지 체크
    query_words = query_lower.split()
    matched_words = sum(1 for word in query_words if word in product_text)
    
    if len(query_words) > 0:
        return matched_words / len(query_words)
    
    return 0.0


def reorder_products(products: List[Product], product_ids: List[int]) -> List[Product]:
    product_map = {product.id: product for product in products}
    ordered_products = [product_map[pid] for pid in product_ids if pid in product_map]
    return ordered_products


# ========================================
# 1. 상품 ID 기반 추천
# ========================================
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
            
    unordered_products = await crud_product.get_products_by_ids(db, product_ids=recommended_product_ids)
    ordered_products = reorder_products(unordered_products, recommended_product_ids)
    return ordered_products


# ========================================
# 2. 텍스트 검색 (★ 하이브리드 ★)
# ========================================
@router.get("/by-text", response_model=List[Product])
async def recommend_by_text_search(
    query: str,
    size: str = None,
    db: AsyncSession = Depends(get_db)
):
    if not koclip_model or not koclip_tokenizer:
        raise HTTPException(status_code=503, detail="AI 모델이 로드되지 않았습니다.")
    
    # ★ 쿼리 확장 ★
    expanded_query = expand_query(query)
    print(f"   원본 쿼리: '{query}'")
    print(f"   확장된 쿼리: '{expanded_query}'")
    print(f"   사이즈 필터: {size}")
        
    try:
        # ★ 올바른 텍스트 인코딩 (확장된 쿼리 사용) ★
        text_inputs = koclip_tokenizer(
            expanded_query,  # ← 확장된 쿼리
            return_tensors="pt", 
            padding=True, 
            truncation=True,
            max_length=77
        ).to(DEVICE)
        
        with torch.no_grad():
            text_features = koclip_model.get_text_features(**text_inputs)
            # 정규화 (중요!)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        target_vector = text_features[0].cpu().numpy().tolist()
        print(f" 쿼리 벡터 생성 완료. 벡터 차원: {len(target_vector)}")
        
    except Exception as e:
        print(f" 텍스트 벡터화 오류: {e}")
        raise HTTPException(status_code=500, detail=f"텍스트 벡터화 실패: {e}")

    all_vectors_data = await crud_recommend.get_all_text_vectors(db, size=size)
    
    print(f" 비교할 상품 수: {len(all_vectors_data)}")
    
    if not all_vectors_data:
        raise HTTPException(
            status_code=404, 
            detail=f"'{size}' 사이즈에 해당하는 상품이 없습니다." if size else "비교할 상품이 없습니다."
        )

    # ★ AI 유사도 계산 (더 많이 가져오기) ★
    top_n_results = crud_recommend.get_top_n_similar_products(
        target_vector, 
        all_vectors_data, 
        n=min(20, len(all_vectors_data))  # 최대 20개 또는 전체
    )
    
    # ★ 상품 정보 가져오기 (키워드 매칭용) ★
    candidate_ids = [pid for pid, score in top_n_results]
    candidate_products = await crud_product.get_products_by_ids(db, product_ids=candidate_ids)
    
    # ★ 하이브리드 점수 계산 ★
    product_map = {p.id: p for p in candidate_products}
    hybrid_scores = []
    
    for pid, ai_score in top_n_results:
        if pid not in product_map:
            continue
            
        product = product_map[pid]
        keyword_score = calculate_keyword_score(
            query,  # ← 원본 쿼리로 키워드 매칭
            product.name, 
            product.description or ""
        )
        
        # ★ 하이브리드 점수: AI 60% + 키워드 40% ★
        # (키워드 가중치를 높여서 정확도 향상)
        hybrid_score = (ai_score * 0.6) + (keyword_score * 0.4)
        
        hybrid_scores.append((pid, hybrid_score, ai_score, keyword_score))
    
    # 하이브리드 점수로 재정렬
    hybrid_scores.sort(key=lambda x: x[1], reverse=True)
    
    # ★ 디버깅 출력 ★
    print(" Top 5 하이브리드 검색 결과:")
    for pid, hybrid, ai, keyword in hybrid_scores[:5]:
        product_name = product_map[pid].name[:35]
        print(f"  [{pid}] {product_name}")
        print(f"        AI: {ai:.4f} | 키워드: {keyword:.4f} | 최종: {hybrid:.4f}")

    # 상위 5개만 반환
    recommended_product_ids = [pid for pid, _, _, _ in hybrid_scores[:5]]
    unordered_products = await crud_product.get_products_by_ids(db, product_ids=recommended_product_ids)
    ordered_products = reorder_products(unordered_products, recommended_product_ids)
    
    return ordered_products


# ========================================
# 3. 이미지 업로드 검색
# ========================================
@router.post("/by-image-upload", response_model=List[Product])
async def recommend_by_image_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    if not koclip_model or not koclip_image_processor:
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
        
        # ★ 올바른 이미지 전처리 ★
        pixel_values = koclip_image_processor(
            images=image_rgb, 
            return_tensors="pt"
        )['pixel_values'].to(DEVICE)
        
        with torch.no_grad():
            image_features = koclip_model.get_image_features(pixel_values=pixel_values)
            # 정규화
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        target_vector = image_features[0].cpu().numpy().tolist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 벡터화에 실패했습니다: {e}")

    all_vectors_data = await crud_recommend.get_all_vectors(db)
    if not all_vectors_data:
        raise HTTPException(status_code=404, detail="비교할 상품 이미지 벡터가 DB에 없습니다.")

    top_n_results = crud_recommend.get_top_n_similar_products(
        target_vector, 
        all_vectors_data, 
        n=5
    )

    recommended_product_ids = [pid for pid, score in top_n_results[:5]]
    unordered_products = await crud_product.get_products_by_ids(db, product_ids=recommended_product_ids)
    ordered_products = reorder_products(unordered_products, recommended_product_ids)
    
    return ordered_products