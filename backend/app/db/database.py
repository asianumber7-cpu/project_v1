# backend/app/db/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. MySQL DB 접속 정보 (★팀원마다 다를 수 있음★)
# "mysql+asyncmy://[유저명]:[패스워드]@[DB주소]:[포트]/[DB이름]"
# 예: "mysql+asyncmy://root:1234@localhost:3306/my_shoppingmall"
# ★★★ 본인의 MySQL 환경에 맞게 수정하세요 ★★★
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "mysql+asyncmy://root:password@localhost:3306/project_v1_db"
)

# 2. 비동기 엔진 생성
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# 3. 비동기 세션 생성
# autocommit=False: 데이터를 변경할 때 commit()을 수동으로 호출
# autoflush=False: 세션 내에서 쿼리 결과를 자동으로 플러시하지 않음
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, autocommit=False, autoflush=False
)

# 4. SQLAlchemy 모델의 기반이 될 Base 클래스 생성
# 앞으로 만들 모든 DB 모델(테이블)이 이 Base를 상속받아야 합니다.
Base = declarative_base()

# (참고) FastAPI에서 DB 세션을 사용하기 위한 의존성 함수
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session