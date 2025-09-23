from fastapi import FastAPI
from fastapi.security import HTTPBearer
from database import Base, engine
from routers import health, auth, users, pictures, comments, categories

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