# backend/Dockerfile (★ 최적화 버전 ★)

# ===== 1단계: 빌드 스테이지 =====
FROM python:3.11.14-slim AS builder

WORKDIR /app

# 필요한 시스템 패키지 설치 (빌드 도구)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 먼저 복사 (캐싱 최적화)
COPY requirements.txt .

# 파이썬 라이브러리 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ===== 2단계: 프로덕션 스테이지 =====
FROM python:3.11.14-slim

WORKDIR /app

# 런타임에 필요한 시스템 패키지만 설치
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 빌드 스테이지에서 설치된 파이썬 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 백엔드 소스 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 헬스체크 (선택사항)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget -q --spider http://localhost:8000/ || exit 1

# 서버 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]