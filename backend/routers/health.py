from fastapi import APIRouter
from database import db
from sqlalchemy import text

router = APIRouter(tags=["health"])

@router.get("/api/health")
def health_check():
    result = db.session.execute(text("SELECT message FROM health_check LIMIT 1")).fetchone()
    if result:
        return {"status": "ok", "message": result[0]}
    return {"status": "error", "message": "Database query failed"}