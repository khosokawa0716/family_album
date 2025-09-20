from fastapi import APIRouter, HTTPException
from database import db
from models import User
from schemas import UserCreate, UserResponse
from auth import pwd_context

router = APIRouter(prefix="/api", tags=["users"])

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    hashed_password = pwd_context.hash(user.password)

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