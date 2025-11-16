# backend/app/batch_embed.py (★ 완전 수정 ★)

import asyncio
import httpx
import io
import logging
from PIL import Image
from transformers import VisionTextDualEncoderModel, AutoTokenizer, AutoImageProcessor
import torch
from sqlalchemy.future import select

from app.db.database import AsyncSessionLocal
from app.models.product import Product
from app.models.product_vector import ProductVector 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ★ KoCLIP 올바른 사용법 ★
MODEL_NAME = 'koclip/koclip-base-pt'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

async def fetch_image_from_url(url: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content))
            return image
    except Exception as e:
        logger.error(f"이미지 다운로드 실패 (URL: {url}): {e}")
        return None

async def main():
    logger.info("AI 배치 스크립트 시작...")
    
    logger.info(f"'{MODEL_NAME}' 모델을 로드합니다...")
    try:
        # ★ 올바른 KoCLIP 로딩 방법 ★
        model = VisionTextDualEncoderModel.from_pretrained(MODEL_NAME).to(DEVICE)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        image_processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
        
        model.eval()  # 평가 모드로 설정
        logger.info(f"모델 로드 완료. (Device: {DEVICE})")
    except Exception as e:
        logger.error(f"모델 로드 중 오류 발생: {e}")
        return

    async with AsyncSessionLocal() as session:
        logger.info("DB 세션 생성 완료.")
        
        stmt = (
            select(Product)
            .outerjoin(ProductVector, Product.id == ProductVector.product_id)
            .filter(
                (ProductVector.id == None) | (Product.text_vector == None)
            )
        )
        result = await session.execute(stmt)
        products_to_process = result.scalars().all()

        if not products_to_process:
            logger.info("벡터화할 새 상품이 없습니다. 종료합니다.")
            return

        logger.info(f"총 {len(products_to_process)}개의 새 상품을 벡터화합니다.")

        for product in products_to_process:
            logger.info(f"[Product ID: {product.id}] '{product.name}' 처리 중...")
            
            # --- 1. 텍스트 벡터 생성 ---
            try:
                text_to_embed = f"{product.name} {product.description}"
                
                # ★ 올바른 텍스트 인코딩 ★
                text_inputs = tokenizer(
                    text_to_embed, 
                    return_tensors="pt", 
                    padding=True, 
                    truncation=True,
                    max_length=77
                ).to(DEVICE)
                
                with torch.no_grad():
                    text_features = model.get_text_features(**text_inputs)
                    # 정규화 (중요!)
                    text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                text_vector = text_features[0].cpu().numpy().tolist()
                
                product.text_vector = text_vector 
                session.add(product) 
                logger.info(f"[Product ID: {product.id}] 텍스트 벡터 생성 완료.")
            except Exception as e:
                logger.error(f"[Product ID: {product.id}] 텍스트 벡터화 실패: {e}")

            # --- 2. 이미지 벡터 생성 ---
            image = await fetch_image_from_url(product.image_url)
            if image is None:
                logger.warning(f"[Product ID: {product.id}] 이미지 처리 실패. 건너뜁니다.")
                continue

            try:
                image_rgb = image.convert("RGB")
                
                # ★ 올바른 이미지 전처리 ★
                pixel_values = image_processor(
                    images=image_rgb, 
                    return_tensors="pt"
                )['pixel_values'].to(DEVICE)
                
                with torch.no_grad():
                    image_features = model.get_image_features(pixel_values=pixel_values)
                    # 정규화 (중요!)
                    image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
                vector = image_features[0].cpu().numpy().tolist()
                
                db_vector = ProductVector(
                    product_id=product.id,
                    vector=vector
                )
                session.add(db_vector)
                logger.info(f"[Product ID: {product.id}] 이미지 벡터 생성 완료.")
            except Exception as e:
                logger.error(f"[Product ID: {product.id}] 이미지 벡터화 실패: {e}")

        try:
            await session.commit()
            logger.info("모든 벡터를 DB에 성공적으로 저장했습니다.")
        except Exception as e:
            await session.rollback()
            logger.error(f"DB 커밋 중 오류 발생: {e}")

    logger.info("AI 배치 스크립트 종료.")

if __name__ == "__main__":
    asyncio.run(main())