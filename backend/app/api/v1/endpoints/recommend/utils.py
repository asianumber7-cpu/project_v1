# backend/app/api/v1/endpoints/recommend/utils.py

import re
from typing import List
from transformers import VisionTextDualEncoderModel, AutoTokenizer, AutoImageProcessor
import torch

from app.schemas.product import Product

# ========================================
# 모델 설정
# ========================================
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

# ========================================
# 키워드 확장 사전
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

def calculate_keyword_score(query: str, product_name: str, product_description: str) -> float:
    """키워드 매칭 점수 계산 (0.0 ~ 1.0)"""
    query_clean = re.sub(r'[^\w\s]', ' ', query.lower())
    query_clean = query_clean.replace('_', ' ')
    
    product_text = f"{product_name} {product_description}".lower()
    product_text = re.sub(r'[^\w\s]', ' ', product_text)
    product_text = product_text.replace('_', ' ')
    
    query_words = set(word for word in query_clean.split() if len(word) >= 2)
    product_words = set(word for word in product_text.split() if len(word) >= 2)
    
    if not query_words:
        return 0.0
    
    common_words = query_words & product_words
    
    if common_words:
        print(f"      [DEBUG] '{query}' vs '{product_name}'")
        print(f"              공통 단어: {common_words} → 점수: {len(common_words) / len(query_words):.4f}")
    
    return len(common_words) / len(query_words)

def reorder_products(products: List[Product], product_ids: List[int]) -> List[Product]:
    """상품 리스트를 ID 순서대로 재정렬"""
    product_map = {product.id: product for product in products}
    ordered_products = [product_map[pid] for pid in product_ids if pid in product_map]
    return ordered_products