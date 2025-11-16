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

# (★학생님이 등록했던 10개의 상품 데이터★)
PRODUCT_DATA = [
    {
        "name": "회색 깃발크립 와이드 핏 트레이닝 팬츠",
        "description": "가을용 트레이닝 조거 팬츠 지크립 바지",
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20240802/4292299/4292299_17225758319642_big.png?w=1200",
        "size_info": {"M": 10, "L": 20}
    },
    {
        "name": "회색 깃발크립 와이드 핏 트레이닝 팬츠", # (ID 2 - 이름 중복이지만 테스트용으로 OK)
        "description": "가을용 트레이닝 조거 팬츠 지크립 바지",
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20240802/4292299/4292299_17225758319642_big.png?w=1200",
        "size_info": {"M": 10, "L": 20}
    },
    {
        "name": "회색 깃발크립 와이드 핏 트레이닝 팬츠", # (ID 3 - 이름 중복이지만 테스트용으로 OK)
        "description": "가을용 트레이닝 조거 팬츠 지크립 바지",
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20240802/4292299/4292299_17225758319642_big.png?w=1200",
        "size_info": {"M": 10, "L": 20}
    },
    {
        "name": "P2403 배색 와이드 트랙팬츠",
        "description": "배색 와이드 트랙팬츠",
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20241011/4508722/4508722_17286278760083_big.jpg?w=1200",
        "size_info": {"S": 5, "M": 10}
    },
    {
        "name": "시그니처 밴드 나일론 조거 팬츠 (BLACK)",
        "description": "나일론 조거 팬츠",
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20251028/5652489/5652489_17616242676562_big.jpg?w=1200",
        "size_info": {"L": 15, "XL": 10}
    },
    {
        "name": "[기모원단추가]88 크로스 백 패치 스웨트 팬츠",
        "description": "기모 스웨트 팬츠",
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20250808/5306789/5306789_17557676327782_big.jpg?w=1200",
        "size_info": {"M": 10, "L": 10}
    },
    {
        "name": "501® 오리지널 RIGID 진_00501-0000",
        "description": "오리지널 데님",
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20220317/2425479/2425479_17182629052451_big.jpg?w=1200",
        "size_info": {"30": 5, "32": 10, "34": 5}
    },
    {
        "name": "Sun Dance Denim Pants - Black",
        "description": "자수 데님 팬츠",
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20240131/3836236/3836236_17147196759244_big.png?w=1200",
        "size_info": {"M": 10, "L": 10}
    },
    {
        "name": "스웨이드 무스탕_카멜",
        "description": "스웨이드 무스탕",
        "image_url": "https://image.msscdn.net/thumbnails/images/goods_img/20251014/5586316/5586316_17610321361157_big.jpg?w=1200",
        "size_info": {"FREE": 20}
    },
    {
        "name": "리얼 B3 무스탕 자켓 맨 (블랙)",
        "description": "B3 무스탕 자켓",
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