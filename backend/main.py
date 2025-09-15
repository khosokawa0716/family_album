from fastapi import FastAPI
from database import db
from sqlalchemy import text

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI backend!"}

@app.get("/health")
def health_check():
    result = db.session.execute(text("SELECT message FROM health_check LIMIT 1")).fetchone()
    if result:
        return {"status": "ok", "message": result[0]}
    return {"status": "error", "message": "Database query failed"}