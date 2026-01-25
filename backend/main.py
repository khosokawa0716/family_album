import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.security import HTTPBearer
from database import Base, engine
from routers import health, auth, users, pictures, comments, categories, logs

# CORS設定（環境変数 CORS_ORIGINS でカンマ区切りで指定、未設定時はすべて許可）
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]

app = FastAPI(
    title="Family Album API",
    description="Family Album Backend API",
    version="1.0.0"
)

# Swagger UI用のセキュリティスキーム設定
security = HTTPBearer()

Base.metadata.create_all(bind=engine)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(pictures.router)
app.include_router(comments.router)
app.include_router(categories.router)
app.include_router(logs.router)
# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
