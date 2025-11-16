# backend/app/seed.py

import asyncio
import logging
from sqlalchemy.future import select

from app.db.database import AsyncSessionLocal
from app.models.product import Product
# (중요) SQLAlchemy가 관계를 인식하도록 모든 모델을 임포트
from app.models import user, product_vector 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



PRODUCT_DATA = [
    {
        "name": "회색 깃발크립 와이드 핏 트레이닝 팬츠",
        "description": "가을용 트레이닝 조거 팬츠 편안한 와이드 핏 운동복",  # ← 개선
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20240802/4292299/4292299_17225758319642_big.png?w=1200",
        "size_info": {"M": 10, "L": 20}
    },
    {
        "name": "회색 깃발크립 와이드 핏 트레이닝 팬츠",
        "description": "가을용 트레이닝 조거 팬츠 편안한 와이드 핏 운동복",  # ← 개선
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20240802/4292299/4292299_17225758319642_big.png?w=1200",
        "size_info": {"M": 10, "L": 20}
    },
    {
        "name": "회색 깃발크립 와이드 핏 트레이닝 팬츠",
        "description": "가을용 트레이닝 조거 팬츠 편안한 와이드 핏 운동복",  # ← 개선
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20240802/4292299/4292299_17225758319642_big.png?w=1200",
        "size_info": {"M": 10, "L": 20}
    },
    {
        "name": "P2403 배색 와이드 트랙팬츠",
        "description": "배색 디자인 와이드 트랙 팬츠 편안한 핏",  # ← 개선
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20241011/4508722/4508722_17286278760083_big.jpg?w=1200",
        "size_info": {"S": 5, "M": 10}
    },
    {
        "name": "시그니처 밴드 나일론 조거 팬츠 (BLACK)",
        "description": "블랙 나일론 조거 팬츠 시그니처 밴드 디자인",  # ← 개선
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20251028/5652489/5652489_17616242676562_big.jpg?w=1200",
        "size_info": {"L": 15, "XL": 10}
    },
    {
        "name": "[기모원단추가]88 크로스 백 패치 스웨트 팬츠",
        "description": "기모 안감 크로스 백 패치 스웨트 팬츠 겨울용",  # ← 개선
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20250808/5306789/5306789_17557676327782_big.jpg?w=1200",
        "size_info": {"M": 10, "L": 10}
    },
    {
        "name": "501® 오리지널 RIGID 진_00501-0000",
        "description": "리바이스 501 오리지널 리지드 데님 청바지 진",  # ← 개선
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20220317/2425479/2425479_17182629052451_big.jpg?w=1200",
        "size_info": {"30": 5, "32": 10, "34": 5}
    },
    {
        "name": "Sun Dance Denim Pants - Black",
        "description": "블랙 데님 청바지 자수 디자인 팬츠",  # ← 개선
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20240131/3836236/3836236_17147196759244_big.png?w=1200",
        "size_info": {"M": 10, "L": 10}
    },
    {
        "name": "스웨이드 무스탕 카멜",  # ← 언더스코어 제거
        "description": "카멜 컬러 스웨이드 무스탕 자켓 양털 안감",  # ← 개선
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20251014/5586316/5586316_17610321361157_big.jpg?w=1200",
        "size_info": {"FREE": 20}
    },
    {
        "name": "리얼 B3 무스탕 자켓 맨 (블랙)",
        "description": "블랙 B3 무스탕 자켓 양털 리얼 레더",  # ← 개선
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20181128/914738/914738_16992551007717_big.jpg?w=1200",
        "size_info": {"L": 5, "XL": 5}
    }
]

async def seed_data():
    async with AsyncSessionLocal() as session:
        # 1. 혹시 모르니 첫 번째 상품이 이미 있는지 확인
        result = await session.execute(
            select(Product).filter(Product.name == PRODUCT_DATA[0]['name'])
        )
        if result.scalars().first():
            logger.info("데이터가 이미 존재합니다. 시딩을 건너뜁니다.")
            return

        logger.info("새로운 상품 데이터를 시딩합니다...")
        
        # 2. 10개 상품을 DB에 추가
        for item in PRODUCT_DATA:
            new_product = Product(
                name=item['name'],
                description=item['description'],
                image_url=item['image_url'],
                size_info=item['size_info']
            )
            session.add(new_product)
        
        # 3. DB에 최종 커밋
        try:
            await session.commit()
            logger.info("10개 상품 데이터 시딩 완료.")
        except Exception as e:
            await session.rollback()
            logger.error(f"데이터 시딩 중 오류 발생: {e}")

async def main():
    logger.info("시딩 스크립트 시작...")
    await seed_data()
    logger.info("시딩 스크립트 종료.")

if __name__ == "__main__":
    asyncio.run(main())