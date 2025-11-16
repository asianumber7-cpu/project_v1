# backend/app/main.py (★최종 수정본★)

from fastapi import FastAPI
from app.api.v1.api import api_router
from fastapi.middleware.cors import CORSMiddleware 

app = FastAPI(
    title="AI Shopping Mall Project"
)

# (★수정★) 5173을 5174로 변경
origins = [
    "http://localhost:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Shopping Mall API"}