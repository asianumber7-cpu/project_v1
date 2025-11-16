# backend/app/api/v1/endpoints/recommend.py (★ 완전 최종 버전 ★)

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from transformers import VisionTextDualEncoderModel, AutoTokenizer, AutoImageProcessor
import torch
import io
from PIL import Image
import numpy as np
import re

from app.db.database import get_db
from app.schemas.product import Product
from app.models.product import Product as ProductModel
from app.crud import crud_recommend, crud_product

# ★ KoCLIP 설정 ★
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
    for key, expanded in KEYWORD_EXPANSIONS.items():
        if key in query_lower:
            return expanded
    return query

# backend/app/api/v1/endpoints/recommend.py

def calculate_keyword_score(query: str, product_name: str, product_description: str) -> float:
    """
    키워드 매칭 점수 계산 (0.0 ~ 1.0)
    ★ 언더스코어, 특수문자를 공백으로 치환 후 비교 ★
    """
    # ★ 특수문자를 모두 공백으로 변환 ★
    query_clean = re.sub(r'[^\w\s]', ' ', query.lower())
    query_clean = query_clean.replace('_', ' ')  # 언더스코어도 공백으로
    
    product_text = f"{product_name} {product_description}".lower()
    product_text = re.sub(r'[^\w\s]', ' ', product_text)
    product_text = product_text.replace('_', ' ')
    
    # 단어 추출 (2글자 이상)
    query_words = set(word for word in query_clean.split() if len(word) >= 2)
    product_words = set(word for word in product_text.split() if len(word) >= 2)
    
    if not query_words:
        return 0.0
    
    # 공통 단어 찾기
    common_words = query_words & product_words
    
    # 디버깅
    if common_words:
        print(f"      [DEBUG] '{query}' vs '{product_name}'")
        print(f"              쿼리 단어: {query_words}")
        print(f"              상품 단어: {product_words}")
        print(f"              공통 단어: {common_words} → 점수: {len(common_words) / len(query_words):.4f}")
    
    return len(common_words) / len(query_words)

def reorder_products(products: List[Product], product_ids: List[int]) -> List[Product]:
    product_map = {product.id: product for product in products}
    ordered_products = [product_map[pid] for pid in product_ids if pid in product_map]
    return ordered_products


# ========================================
# 1. 상품 ID 기반 추천 (★ 최종 버전 ★)
# ========================================
@router.get("/by-product/{product_id}", response_model=List[Product])
async def recommend_similar_products(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    print(f"\n{'='*70}")
    print(f"🔍 상품 ID {product_id} 기반 하이브리드 추천 (이미지 + 키워드)")
    print(f"{'='*70}")
    
    # 1. 기준 상품 가져오기
    base_product_result = await db.execute(
        select(ProductModel).filter(ProductModel.id == product_id)
    )
    base_product = base_product_result.scalars().first()
    
    if not base_product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    print(f"📦 기준 상품: [{product_id}] {base_product.name}")
    
    # 2. 이미지 벡터로 유사도 계산
    target_image_vector = await crud_recommend.get_vector_by_product_id(db, product_id)
    if not target_image_vector:
        raise HTTPException(status_code=404, detail="기준 상품의 이미지 벡터를 찾을 수 없습니다.")
    
    print(f"✅ 이미지 벡터 차원: {len(target_image_vector)}")

    all_image_vectors = await crud_recommend.get_all_vectors(db)
    print(f"📊 비교할 상품 수: {len(all_image_vectors)}")

    image_similarity_results = crud_recommend.get_top_n_similar_products(
        target_image_vector, 
        all_image_vectors, 
        n=len(all_image_vectors)
    )
    
    image_scores = {pid: score for pid, score in image_similarity_results}
    
    # 3. 모든 상품 정보 가져오기
    all_candidate_ids = [pid for pid, _ in image_similarity_results if pid != product_id]
    candidates_result = await db.execute(
        select(ProductModel).filter(ProductModel.id.in_(all_candidate_ids))
    )
    candidates = candidates_result.scalars().all()
    product_map = {p.id: p for p in candidates}
    
# 4번 섹션의 하이브리드 점수 계산 부분만 수정

    # 4. 하이브리드 점수 계산 (★ 키워드 70% + 이미지 30% ★)
    hybrid_scores = []
    
    for pid, product in product_map.items():
        img_score = image_scores.get(pid, 0.0)
        
        # 키워드 매칭
        keyword_score = calculate_keyword_score(
            base_product.name,
            product.name,
            product.description or ""
        )
        
        # ★ 하이브리드 점수: 키워드 70% + 이미지 30% ★
        # (상품 추천에서는 카테고리/키워드가 더 중요)
        hybrid_score = (keyword_score * 0.7) + (img_score * 0.3)
        
        hybrid_scores.append((pid, hybrid_score, img_score, keyword_score))
    
    # 정렬
    hybrid_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 5. 디버깅 출력
    print(f"\n🎯 Top 10 하이브리드 추천 결과:")
    print(f"{'-'*90}")
    for i, (pid, hybrid, img, kwd) in enumerate(hybrid_scores[:10], 1):
        name = product_map[pid].name[:35]
        print(f"  {i}. [ID:{pid:2d}] 최종: {hybrid:.4f} | 이미지: {img:+.4f} | 키워드: {kwd:.4f}")
        print(f"       └─ {name}")
    print(f"{'-'*90}\n")
    
    # 6. 상위 5개 반환
    recommended_product_ids = [pid for pid, _, _, _ in hybrid_scores[:5]]
    print(f"✅ 최종 추천: {recommended_product_ids}")
    print(f"{'='*70}\n")
    
    unordered_products = await crud_product.get_products_by_ids(db, product_ids=recommended_product_ids)
    ordered_products = reorder_products(unordered_products, recommended_product_ids)
    return ordered_products


# ========================================
# 2. 텍스트 검색 (하이브리드)
# ========================================
@router.get("/by-text", response_model=List[Product])
async def recommend_by_text_search(
    query: str,
    size: str = None,
    db: AsyncSession = Depends(get_db)
):
    if not koclip_model or not koclip_tokenizer:
        raise HTTPException(status_code=503, detail="AI 모델이 로드되지 않았습니다.")
    
    expanded_query = expand_query(query)
    print(f"🔍 원본: '{query}' → 확장: '{expanded_query}'")
        
    try:
        text_inputs = koclip_tokenizer(
            expanded_query,
            return_tensors="pt", 
            padding=True, 
            truncation=True,
            max_length=77
        ).to(DEVICE)
        
        with torch.no_grad():
            text_features = koclip_model.get_text_features(**text_inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        
        target_vector = text_features[0].cpu().numpy().tolist()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"텍스트 벡터화 실패: {e}")

    all_vectors_data = await crud_recommend.get_all_text_vectors(db, size=size)
    
    if not all_vectors_data:
        raise HTTPException(
            status_code=404, 
            detail=f"'{size}' 사이즈에 해당하는 상품이 없습니다." if size else "비교할 상품이 없습니다."
        )

    top_n_results = crud_recommend.get_top_n_similar_products(
        target_vector, 
        all_vectors_data, 
        n=min(20, len(all_vectors_data))
    )
    
    candidate_ids = [pid for pid, score in top_n_results]
    candidate_products = await crud_product.get_products_by_ids(db, product_ids=candidate_ids)
    
    product_map = {p.id: p for p in candidate_products}
    hybrid_scores = []
    
    for pid, ai_score in top_n_results:
        if pid not in product_map:
            continue
            
        product = product_map[pid]
        keyword_score = calculate_keyword_score(
            query,
            product.name, 
            product.description or ""
        )
        
        hybrid_score = (ai_score * 0.6) + (keyword_score * 0.4)
        hybrid_scores.append((pid, hybrid_score, ai_score, keyword_score))
    
    hybrid_scores.sort(key=lambda x: x[1], reverse=True)
    
    print("🎯 Top 5 하이브리드 검색 결과:")
    for pid, hybrid, ai, keyword in hybrid_scores[:5]:
        product_name = product_map[pid].name[:35]
        print(f"  [{pid}] {product_name}")
        print(f"        AI: {ai:.4f} | 키워드: {keyword:.4f} | 최종: {hybrid:.4f}")

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
        pixel_values = koclip_image_processor(
            images=image_rgb, 
            return_tensors="pt"
        )['pixel_values'].to(DEVICE)
        
        with torch.no_grad():
            image_features = koclip_model.get_image_features(pixel_values=pixel_values)
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