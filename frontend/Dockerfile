# ===== 1단계: 빌드 스테이지 =====
FROM node:18-alpine AS builder

WORKDIR /app

# package.json과 package-lock.json 복사
COPY package*.json ./

# 의존성 설치
RUN npm ci

# 소스 코드 전체 복사
COPY . .

# Vite 빌드 실행 (dist 폴더 생성)
RUN npm run build

# ===== 2단계: 프로덕션 스테이지 =====
FROM nginx:1.25-alpine

# Nginx 기본 설정 삭제
RUN rm /etc/nginx/nginx.conf

# 커스텀 Nginx 설정 복사
COPY ./nginx.conf /etc/nginx/nginx.conf

# 빌드 스테이지에서 생성된 dist 폴더 복사
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]