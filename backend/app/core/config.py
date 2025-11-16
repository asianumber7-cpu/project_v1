import os

# (★중요★) 이 값은 외부에 노출되면 안 됩니다.
# 실제 배포 시에는 .env 파일 등을 사용해야 합니다.
SECRET_KEY = "gurwnstkddmsfkapsdmfwhgdkgo"  # (다같이 동일하게 사용) 혁준상은라멘을좋아해 <-영어로 변경금지!!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 토큰 만료 시간 (30분)