# backend/app/import_data.py

import asyncio
import json
import os
import logging
from PIL import Image
import torch.nn.functional as F 
from transformers import AutoProcessor, AutoModel
import torch
from sqlalchemy.future import select

from app.db.database import AsyncSessionLocal, engine, Base
from app.models.product import Product
from app.models.product_vector import ProductVector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = 'koclip/koclip-base-pt'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

DATA_DIR = "app/data"
JSON_FILE = os.path.join(DATA_DIR, "products.json")
IMAGE_DIR = os.path.join(DATA_DIR, "images")

async def import_json_data():
    logger.info("데이터 임포트 시작...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("데이터베이스 테이블 생성 완료.")

    if not os.path.exists(JSON_FILE):
        logger.error(f"JSON 파일을 찾을 수 없습니다: {JSON_FILE}")
        return

    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        product_list = json.load(f)

    logger.info(f"총 {len(product_list)}개의 상품을 처리합니다.")

    try:
        logger.info(f"'{MODEL_NAME}' 모델 로드 중...")
        model = AutoModel.from_pretrained(MODEL_NAME).to(DEVICE)
        processor = AutoProcessor.from_pretrained(MODEL_NAME)
        logger.info("모델 로드 완료.")
    except Exception as e:
        logger.error(f"모델 로드 실패: {e}")
        return

    async with AsyncSessionLocal() as session:
        # ★ 기존 상품명 조회 (중복 방지)
        existing_result = await session.execute(select(Product.name))
        existing_names = {row[0] for row in existing_result.all()}
        logger.info(f"기존 상품 {len(existing_names)}개 발견")

        for item in product_list:
            filename = item.get("image_filename")
            product_name = item.get("product_name")

            # ★ 중복 체크
            if product_name in existing_names:
                logger.warning(f"⏭️ 이미 존재함 (건너뜀): {product_name}")
                continue
            
            image_path = os.path.join(IMAGE_DIR, filename)
            if not os.path.exists(image_path):
                logger.warning(f"이미지 파일 없음: {filename} (건너뜀)")
                continue

            logger.info(f"처리 중: {product_name}")

            try:
                # 1. 이미지 벡터 생성
                image = Image.open(image_path)
                image_rgb = image.convert("RGB")
                
                inputs_img = processor(images=[image_rgb], return_tensors="pt").to(DEVICE)
                img_features = model.get_image_features(**inputs_img)
                img_features = F.normalize(img_features, p=2, dim=1)
                img_vector = img_features[0].cpu().detach().numpy().tolist()

                # 2. 텍스트 벡터 생성
                description = item.get("description", "")
                brand_val = item.get("brand", "")
                color_val = item.get("color", "")
                
                text_to_embed = f"{product_name} {product_name} {product_name} {brand_val} {color_val} {description}"
                
                inputs_text = processor(
                    text=text_to_embed, 
                    return_tensors="pt", 
                    padding=True, 
                    truncation=True, 
                    max_length=77
                ).to(DEVICE)
                text_features = model.get_text_features(**inputs_text)
                text_features = F.normalize(text_features, p=2, dim=1)
                text_vector = text_features[0].cpu().detach().numpy().tolist()

                # 3. DB 저장
                size_str = item.get("size", "")
                size_json = {s.strip(): 10 for s in size_str.split(',')} if size_str else {}
                price_val = item.get("price", 0)
                season_val = item.get("season", "")

                new_product = Product(
                    name=product_name,
                    description=description,
                    image_url=f"http://localhost:8000/static/images/{filename}",
                    size_info=size_json,
                    text_vector=text_vector,
                    price=price_val,
                    brand=brand_val,
                    color=color_val,
                    season=season_val
                )
                
                session.add(new_product)
                await session.flush()
                
                # ★ 중복 방지 목록에 추가
                existing_names.add(product_name)

                db_vector = ProductVector(
                    product_id=new_product.id,
                    vector=img_vector
                )
                session.add(db_vector)

            except Exception as e:
                logger.error(f"처리 중 오류 발생 ({product_name}): {e}")
                continue

        try:
            await session.commit()
            logger.info("✅ 모든 데이터 임포트 및 벡터화 완료!")
        except Exception as e:
            await session.rollback()
            logger.error(f"DB 저장 중 오류: {e}")

if __name__ == "__main__":
    asyncio.run(import_json_data())