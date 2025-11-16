# backend/app/scripts/regenerate_text_vectors.py (새 파일)

import asyncio
import logging
from transformers import VisionTextDualEncoderModel, AutoTokenizer
import torch
from sqlalchemy.future import select

from app.db.database import AsyncSessionLocal
from app.models.product import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = 'koclip/koclip-base-pt'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

async def main():
    logger.info("★ 텍스트 벡터 재생성 스크립트 시작 ★")
    
    logger.info(f"'{MODEL_NAME}' 모델을 로드합니다...")
    try:
        model = VisionTextDualEncoderModel.from_pretrained(MODEL_NAME).to(DEVICE)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model.eval()
        logger.info(f"모델 로드 완료. (Device: {DEVICE})")
    except Exception as e:
        logger.error(f"모델 로드 중 오류 발생: {e}")
        return

    async with AsyncSessionLocal() as session:
        logger.info("DB 세션 생성 완료.")
        
        # ★ 모든 상품 조회 ★
        stmt = select(Product)
        result = await session.execute(stmt)
        all_products = result.scalars().all()

        if not all_products:
            logger.info("처리할 상품이 없습니다.")
            return

        logger.info(f"총 {len(all_products)}개의 상품 텍스트 벡터를 재생성합니다.")

        for product in all_products:
            logger.info(f"[Product ID: {product.id}] '{product.name}' 처리 중...")
            
            try:
                text_to_embed = f"{product.name} {product.description}"
                
                # ★ 텍스트 인코딩 ★
                text_inputs = tokenizer(
                    text_to_embed, 
                    return_tensors="pt", 
                    padding=True, 
                    truncation=True,
                    max_length=77
                ).to(DEVICE)
                
                with torch.no_grad():
                    text_features = model.get_text_features(**text_inputs)
                    # ★★★ 정규화 (L2 norm) ★★★
                    text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                text_vector = text_features[0].cpu().numpy().tolist()
                
                # DB 업데이트
                product.text_vector = text_vector
                session.add(product)
                
                logger.info(f"[Product ID: {product.id}] ✅ 정규화된 텍스트 벡터 생성 완료.")
                
            except Exception as e:
                logger.error(f"[Product ID: {product.id}] 텍스트 벡터화 실패: {e}")

        try:
            await session.commit()
            logger.info("🎉 모든 정규화된 텍스트 벡터를 DB에 성공적으로 저장했습니다.")
        except Exception as e:
            await session.rollback()
            logger.error(f"DB 커밋 중 오류 발생: {e}")

    logger.info("★ 텍스트 벡터 재생성 스크립트 종료 ★")

if __name__ == "__main__":
    asyncio.run(main())