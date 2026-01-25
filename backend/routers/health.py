from fastapi import APIRouter
from database import db
from sqlalchemy import text

router = APIRouter(tags=["health"])

@router.get("/api/health")
def health_check():
    return {"status": "ok"}