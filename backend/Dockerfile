# backend/Dockerfile

# 1. 베이스 이미지: 학생님이 사용한 3.11.14 버전 파이썬
FROM python:3.11.14-slim

# (★수정★) 헬스 체크에 필요한 wget 도구 설치
RUN apt-get update && apt-get install -y wget \
    && rm -rf /var/lib/apt/lists/*

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 라이브러리 설치
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 4. 백엔드 전체 코드 복사
COPY . /app/

# 5. 서버 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]