from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import db, Base, engine
from sqlalchemy import text
from models import User
from schemas import UserCreate, UserResponse, LoginRequest, LoginResponse
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

app = FastAPI()

# JWT設定
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# パスワードハッシュ化の設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# セキュリティ
security = HTTPBearer()

# テーブル作成
Base.metadata.create_all(bind=engine)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_user_by_username(username: str) -> User:
    return db.session.query(User).filter(User.user_name == username).first()

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(username: str, password: str):
    user = get_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI backend!"}

@app.get("/health")
def health_check():
    result = db.session.execute(text("SELECT message FROM health_check LIMIT 1")).fetchone()
    if result:
        return {"status": "ok", "message": result[0]}
    return {"status": "error", "message": "Database query failed"}

@app.post("/api/login", response_model=LoginResponse)
def login(login_request: LoginRequest):
    user = authenticate_user(login_request.user_name, login_request.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ユーザーのstatusが無効（0）の場合はログインを拒否
    if user.status != 1:
        raise HTTPException(
            status_code=403,
            detail="User account is disabled",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.user_name, "user_id": user.id},
        expires_delta=access_token_expires
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

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