# backend/app/core/utils.py

from typing import List, Any

# AI가 추천한 ID 순서대로 상품 리스트를 재정렬하는 함수
# (이 함수는 AI 모델 없이도 테스트할 수 있는 '순수 로직'입니다)
def reorder_products(products: List[Any], product_ids: List[int]) -> List[Any]:
    # 1. product.id를 키로 하는 딕셔너리 생성
    product_map = {product.id: product for product in products}
    
    # 2. product_ids 순서대로 리스트 재구성
    ordered_products = [product_map[pid] for pid in product_ids if pid in product_map]
    
    return ordered_products