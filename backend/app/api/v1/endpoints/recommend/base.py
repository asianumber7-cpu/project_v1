# backend/app/api/v1/endpoints/recommend/base.py

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import torch
import io
from PIL import Image
import numpy as np

from app.db.database import get_db
from app.schemas.product import Product
from app.models.product import Product as ProductModel
from app.crud import crud_recommend, crud_product
from .utils import (
    koclip_model, koclip_tokenizer, koclip_image_processor, DEVICE,
    expand_query, calculate_keyword_score, reorder_products
)

router = APIRouter()


@router.get("/by-product/{product_id}", response_model=List[Product])
async def recommend_by_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
):
    """상품 ID 기반 하이브리드 추천 (이미지 70% + 키워드 30%)"""
    print(f"\n{'='*70}")
    print(f"🔍 상품 ID {product_id} 기반 하이브리드 추천")
    print(f"{'='*70}")
    
    base_product_result = await db.execute(
        select(ProductModel).filter(ProductModel.id == product_id)
    )
    base_product = base_product_result.scalars().first()
    
    if not base_product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    print(f"📦 기준 상품: [{product_id}] {base_product.name}")

    # 성별 감지
    gender = None
    if "여성" in base_product.name or "여자" in base_product.name:
        gender = "여성"
    elif "남성" in base_product.name or "남자" in base_product.name:
        gender = "남성"
    
    target_image_vector = await crud_recommend.get_vector_by_product_id(db, product_id)
    if not target_image_vector:
        raise HTTPException(status_code=404, detail="기준 상품의 이미지 벡터를 찾을 수 없습니다.")
    
    all_image_vectors = await crud_recommend.get_all_vectors(db)
    image_similarity_results = crud_recommend.get_top_n_similar_products(
        target_image_vector, 
        all_image_vectors, 
        n=len(all_image_vectors)
    )
    
    image_scores = {pid: score for pid, score in image_similarity_results}
    
    all_candidate_ids = [pid for pid, _ in image_similarity_results if pid != product_id]
    candidates_result = await db.execute(
        select(ProductModel).filter(ProductModel.id.in_(all_candidate_ids))
    )
    candidates = candidates_result.scalars().all()
    product_map = {p.id: p for p in candidates}
    
    hybrid_scores = []
    for pid, product in product_map.items():
         # 성별 필터링
        if gender == "여성":
            if "여성" not in product.name and "여자" not in product.name:
                continue
        elif gender == "남성":
            if "남성" not in product.name and "남자" not in product.name:
                continue


        img_score = image_scores.get(pid, 0.0)
        keyword_score = calculate_keyword_score(
            base_product.name,
            product.name,
            product.description or ""
        )
        hybrid_score = (keyword_score * 0.7) + (img_score * 0.3)
        hybrid_scores.append((pid, hybrid_score, img_score, keyword_score))
    
    hybrid_scores.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n🎯 Top 5 하이브리드 추천:")
    for i, (pid, hybrid, img, kwd) in enumerate(hybrid_scores[:5], 1):
        print(f"  {i}. [ID:{pid}] 최종: {hybrid:.4f} (이미지: {img:.4f}, 키워드: {kwd:.4f})")
    
    recommended_product_ids = [pid for pid, _, _, _ in hybrid_scores[:5]]
    unordered_products = await crud_product.get_products_by_ids(db, product_ids=recommended_product_ids)
    
    return reorder_products(unordered_products, recommended_product_ids)


@router.get("/by-text", response_model=List[Product])
async def recommend_by_text(
    query: str,
    size: str = None,
    db: AsyncSession = Depends(get_db)
):
    """텍스트 검색 기반 추천 (AI 60% + 키워드 40%)"""
    if not koclip_model or not koclip_tokenizer:
        raise HTTPException(status_code=503, detail="AI 모델이 로드되지 않았습니다.")
    
    expanded_query = expand_query(query)
    print(f"🔍 검색: '{query}' → '{expanded_query}'")
        
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
        raise HTTPException(status_code=404, detail="비교할 상품이 없습니다.")

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
        keyword_score = calculate_keyword_score(query, product.name, product.description or "")
        hybrid_score = (ai_score * 0.6) + (keyword_score * 0.4)
        hybrid_scores.append((pid, hybrid_score, ai_score, keyword_score))
    
    hybrid_scores.sort(key=lambda x: x[1], reverse=True)
    
    recommended_product_ids = [pid for pid, _, _, _ in hybrid_scores[:5]]
    unordered_products = await crud_product.get_products_by_ids(db, product_ids=recommended_product_ids)
    
    return reorder_products(unordered_products, recommended_product_ids)


@router.post("/by-image-upload", response_model=List[Product])
async def recommend_by_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """이미지 업로드 기반 추천"""
    if not koclip_model or not koclip_image_processor:
        raise HTTPException(status_code=503, detail="이미지 AI 모델이 로드되지 않았습니다.")
        
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"이미지 파일 읽기 실패: {e}")
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
        raise HTTPException(status_code=500, detail=f"이미지 벡터화 실패: {e}")

    all_vectors_data = await crud_recommend.get_all_vectors(db)
    if not all_vectors_data:
        raise HTTPException(status_code=404, detail="비교할 상품 벡터가 없습니다.")

    top_n_results = crud_recommend.get_top_n_similar_products(target_vector, all_vectors_data, n=5)
    recommended_product_ids = [pid for pid, score in top_n_results[:5]]
    unordered_products = await crud_product.get_products_by_ids(db, product_ids=recommended_product_ids)
    
    return reorder_products(unordered_products, recommended_product_ids)