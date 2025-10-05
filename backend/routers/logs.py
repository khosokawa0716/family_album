from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import OperationLog, User
from dependencies import get_current_user
from schemas import OperationLogResponse

router = APIRouter(prefix="/api", tags=["logs"])

@router.get("/logs", response_model=List[OperationLogResponse])
def get_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 管理者のみアクセス可能
    if current_user.type != 10:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者のみアクセス可能です"
        )

    try:
        # 操作ログを取得（自家族のログのみ、作成日時の降順）
        logs = db.query(OperationLog, User.user_name).join(
            User, OperationLog.user_id == User.id
        ).filter(
            User.family_id == current_user.family_id
        ).order_by(OperationLog.create_date.desc()).all()

        # レスポンスを構築
        return [
            OperationLogResponse(
                id=log.id,
                user_id=log.user_id,
                user_name=user_name,
                operation=log.operation,
                target_type=log.target_type,
                target_id=log.target_id,
                detail=log.detail,
                create_date=log.create_date
            )
            for log, user_name in logs
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )