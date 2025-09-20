from fastapi import FastAPI, HTTPException
from database import db, Base, engine
from sqlalchemy import text
from models import User
from schemas import UserCreate, UserResponse
from passlib.context import CryptContext

app = FastAPI()

# パスワードハッシュ化の設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# テーブル作成
Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI backend!"}

@app.get("/health")
def health_check():
    result = db.session.execute(text("SELECT message FROM health_check LIMIT 1")).fetchone()
    if result:
        return {"status": "ok", "message": result[0]}
    return {"status": "error", "message": "Database query failed"}

@app.post("/api/users", response_model=UserResponse)
def create_user(user: UserCreate):
    # パスワードをハッシュ化
    hashed_password = pwd_context.hash(user.password)

    # 新しいユーザーを作成
    db_user = User(
        user_name=user.user_name,
        password=hashed_password,
        email=user.email,
        type=user.type,
        family_id=user.family_id
    )

    try:
        db.session.add(db_user)
        db.session.commit()
        db.session.refresh(db_user)
        return db_user
    except Exception as e:
        db.session.rollback()
        raise HTTPException(status_code=400, detail=f"User creation failed: {str(e)}")