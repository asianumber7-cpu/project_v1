# backend/app/batch_embed.py

import asyncio
import httpx  # 비동기 HTTP 요청을 위한 라이브러리 (fastapi[all]에 포함됨)
import io
import logging
from PIL import Image
from sentence_transformers import SentenceTransformer
from sqlalchemy.future import select

# ★중요★ DB 및 모델 임포트
from app.db.database import AsyncSessionLocal
from app.models.product import Product
from app.models.product_vector import ProductVector

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLIP_MODEL = 'clip-ViT-B-32' # 이전 버전
# 사용할 CLIP 모델
# CLIP_MODEL = 'sentence-transformers/clip-ViT-B-32-multilingual-v1'

async def fetch_image_from_url(url: str):
    """비동기적으로 URL에서 이미지를 가져와 PIL Image 객체로 반환"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()  # 200 OK가 아니면 오류 발생
            
            # 응답 콘텐츠(바이트)를 PIL 이미지로 변환
            image = Image.open(io.BytesIO(response.content))
            return image
    except Exception as e:
        logger.error(f"이미지 다운로드 실패 (URL: {url}): {e}")
        return None

async def main():
    logger.info("AI 배치 스크립트 시작...")
    
    # 1. AI 모델 로드
    logger.info(f"'{CLIP_MODEL}' 모델을 로드합니다... (시간이 걸릴 수 있습니다)")
    try:
        model = SentenceTransformer(CLIP_MODEL)
        logger.info("모델 로드 완료.")
    except Exception as e:
        logger.error(f"모델 로드 중 오류 발생: {e}")
        return

    # 2. DB 세션 생성
    async with AsyncSessionLocal() as session:
        logger.info("DB 세션 생성 완료.")
        
        # 3. 벡터가 아직 없는 Product들만 조회
        # (Product.id가 ProductVector.product_id에 없는 것들만)
        stmt = (
            select(Product)
            .outerjoin(ProductVector, Product.id == ProductVector.product_id)
            .filter(ProductVector.id == None)
        )
        result = await session.execute(stmt)
        products_to_process = result.scalars().all()

        if not products_to_process:
            logger.info("벡터화할 새 상품이 없습니다. 종료합니다.")
            return

        logger.info(f"총 {len(products_to_process)}개의 새 상품을 벡터화합니다.")

        # 4. 각 상품을 순회하며 벡터화
        for product in products_to_process:
            logger.info(f"[Product ID: {product.id}] '{product.name}' 처리 중...")
            
            # 4-1. 이미지 다운로드
            image = await fetch_image_from_url(product.image_url)
            
            if image is None:
                logger.warning(f"[Product ID: {product.id}] 이미지 처리 실패. 건너뜁니다.")
                continue

            # 4-2. AI 모델로 이미지 인코딩(벡터화)
            try:

                # model.encode()는 NumPy 배열을 반환하므로 .tolist()로 JSON 변환
                vector = model.encode(image).tolist()

               
                # 4-3. 벡터를 DB에 저장
                db_vector = ProductVector(
                    product_id=product.id,
                    vector=vector
                )
                session.add(db_vector)
                
                logger.info(f"[Product ID: {product.id}] 벡터 생성 및 DB 추가 완료.")

            except Exception as e:
                logger.error(f"[Product ID: {product.id}] 벡터화 실패: {e}")

        # 5. 모든 변경사항을 DB에 최종 커밋
        try:
            await session.commit()
            logger.info("모든 벡터를 DB에 성공적으로 저장했습니다.")
        except Exception as e:
            await session.rollback()
            logger.error(f"DB 커밋 중 오류 발생: {e}")

    logger.info("AI 배치 스크립트 종료.")


if __name__ == "__main__":
    # 이 스크립트를 직접 실행할 때 main() 코루틴을 실행
    asyncio.run(main())