from app.core.utils import reorder_products

# 테스트를 위한 가짜 상품 객체
class MockProduct:
    def __init__(self, id, name):
        self.id = id
        self.name = name

def test_reorder_products():
    """
    AI가 추천한 ID 순서대로 상품 리스트가 잘 정렬되는지 테스트합니다.
    """
    # [준비] 순서가 뒤죽박죽인 상품 리스트 (ID: 10, 20, 30)
    products = [
        MockProduct(id=10, name="상품10"),
        MockProduct(id=20, name="상품20"),
        MockProduct(id=30, name="상품30"),
    ]
    
    # [준비] AI가 추천한 순서 (20 -> 30 -> 10)
    ai_recommend_ids = [20, 30, 10]
    
    # [실행] 함수 호출
    result = reorder_products(products, ai_recommend_ids)
    
    # [검증] 결과가 AI 순서대로 정렬되었는지 확인
    assert result[0].id == 20
    assert result[1].id == 30
    assert result[2].id == 10
    assert len(result) == 3
    print("테스트 통과: 상품 재정렬 로직이 정상입니다.")