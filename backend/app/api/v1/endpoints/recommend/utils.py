# backend/app/api/v1/endpoints/recommend/utils.py

import re
from typing import List
# [수정] AutoModel, AutoProcessor 사용 (Large 모델 호환)
from transformers import AutoModel, AutoProcessor, AutoTokenizer 
import torch

from app.schemas.product import Product

# ========================================
# 모델 설정
# ========================================
MODEL_NAME = 'Bingsu/clip-vit-large-patch14-ko'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

koclip_model = None
koclip_tokenizer = None # Bingsu 모델은 tokenizer 대신 processor를 주로 씁니다
koclip_image_processor = None # 위와 동일

# 통합 프로세서 (추천)
koclip_processor = None

try:
    print("Bingsu (Large) 모델 로딩 시작...")
    # [수정] trust_remote_code=True 추가 및 AutoModel 사용
    koclip_model = AutoModel.from_pretrained(MODEL_NAME, trust_remote_code=True).to(DEVICE)
    
    # Tokenizer와 ImageProcessor가 합쳐진 Processor를 로딩합니다
    koclip_processor = AutoProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)
    
    # 호환성을 위해 변수 매핑 (기존 코드 수정을 최소화하기 위해)
    koclip_tokenizer = koclip_processor 
    koclip_image_processor = koclip_processor
    
    koclip_model.eval()
    print(f"Bingsu (Large) 모델 로드 완료! (Device: {DEVICE})")
except Exception as e:
    print(f"Bingsu 모델 로드 실패: {e}")

# ========================================
# 키워드 확장 사전 (기존 유지)
# ========================================
KEYWORD_EXPANSIONS = {
    "무스탕": "무스탕 자켓 스웨이드 양털 가죽",
    "청바지": "청바지 데님 진 pants",
    "데님": "데님 청바지 진 denim",
    "진": "진 청바지 데님 jeans",
    "후드": "후드 후드티 스웨트 hoodie",
    "트레이닝": "트레이닝 조거 팬츠 운동복",
    "조거": "조거 트레이닝 팬츠 운동복",
    "슬랙스": "슬랙스 정장 바지",
    "맨투맨": "맨투맨 스웨트 셔츠 티셔츠"
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
    # 특수문자 제거 등 전처리
    query_clean = re.sub(r'[^\w\s]', ' ', query.lower())
    product_text = f"{product_name} {product_description}".lower()
    product_text = re.sub(r'[^\w\s]', ' ', product_text)
    
    query_words = set(word for word in query_clean.split() if len(word) >= 2)
    product_words = set(word for word in product_text.split() if len(word) >= 2)
    
    if not query_words:
        return 0.0
    
    common_words = query_words & product_words
    score = len(common_words) / len(query_words)
    
    # 디버깅용 (너무 많이 뜨면 주석 처리)
    # if common_words:
    #     print(f"      [매칭] '{common_words}' -> {score:.2f}")
    
    return score

def reorder_products(products: List[Product], product_ids: List[int]) -> List[Product]:
    """상품 리스트를 ID 순서대로 재정렬"""
    product_map = {product.id: product for product in products}
    ordered_products = [product_map[pid] for pid in product_ids if pid in product_map]
    return ordered_products