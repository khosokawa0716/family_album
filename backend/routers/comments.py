from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from datetime import datetime
import logging

from database import get_db
from models import Picture, User, Comment
from schemas import CommentResponse, CommentCreateRequest, CommentUpdateRequest
from dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["comments"])
logger = logging.getLogger(__name__)


@router.get("/pictures/{picture_id}/comments", response_model=List[CommentResponse])
def get_picture_comments(
    picture_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    写真へのコメント一覧取得API

    指定されたIDの写真に紐づくコメント一覧を取得する。
    家族スコープでのアクセス制御により、自分の家族の写真のコメントのみ取得可能。
    削除済みコメント（is_deleted=1）は除外される。
    コメントは作成日時の昇順でソートされる。

    Args:
        picture_id: コメントを取得する写真のID
        db: データベースセッション
        current_user: 認証済みユーザー情報

    Returns:
        List[CommentResponse]: コメント一覧

    Raises:
        HTTPException:
            - 404: 写真が見つからない、削除済み写真、または他家族の写真
    """

    # 家族スコープでの写真取得（削除済みは除外）
    picture = db.query(Picture).filter(
        and_(
            Picture.id == picture_id,
            Picture.family_id == current_user.family_id,
            Picture.status == 1
        )
    ).first()

    if not picture:
        raise HTTPException(status_code=404, detail="Picture not found")

    # コメント一覧取得（削除済みは除外、作成日時順ソート）
    comments = db.query(Comment).join(User, Comment.user_id == User.id).filter(
        and_(
            Comment.picture_id == picture_id,
            Comment.is_deleted == 0
        )
    ).order_by(Comment.create_date.asc()).all()

    # レスポンス用データ整形
    comment_responses = []
    for comment in comments:
        comment_data = CommentResponse(
            id=comment.id,
            content=comment.content,
            user_id=comment.user_id,
            picture_id=comment.picture_id,
            user_name=comment.user.user_name,
            create_date=comment.create_date,
            update_date=comment.update_date
        )
        comment_responses.append(comment_data)

    return comment_responses


@router.post("/pictures/{picture_id}/comments", response_model=CommentResponse, status_code=201)
def post_picture_comment(
    picture_id: int,
    comment_request: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    写真へのコメント投稿API

    指定されたIDの写真にコメントを投稿する。
    家族スコープでのアクセス制御により、自分の家族の写真にのみコメント投稿可能。
    削除済み写真（status=0）にはコメント投稿不可。

    Args:
        picture_id: コメントを投稿する写真のID
        comment_request: コメント投稿リクエスト
        db: データベースセッション
        current_user: 認証済みユーザー情報

    Returns:
        CommentResponse: 投稿されたコメント情報

    Raises:
        HTTPException:
            - 404: 写真が見つからない、削除済み写真、または他家族の写真
            - 422: リクエストボディのバリデーションエラー
            - 500: データベース保存エラー
    """

    # 家族スコープでの写真取得（削除済みは除外）
    picture = db.query(Picture).filter(
        and_(
            Picture.id == picture_id,
            Picture.family_id == current_user.family_id,
            Picture.status == 1
        )
    ).first()

    if not picture:
        raise HTTPException(status_code=404, detail="Picture not found")

    # コメント作成
    try:
        comment = Comment(
            content=comment_request.content,
            user_id=current_user.id,
            picture_id=picture_id,
            is_deleted=0
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)

        # ユーザー情報を含む完全なコメントオブジェクトを取得
        comment_with_user = db.query(Comment).join(User).filter(Comment.id == comment.id).first()

        logger.info(f"Comment created: ID={comment.id}, User={current_user.id}, Picture={picture_id}")
        return CommentResponse.from_comment(comment_with_user)

    except Exception as e:
        logger.error(f"Failed to create comment for picture {picture_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create comment")


@router.patch("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int,
    update_request: CommentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    コメント編集API

    指定されたIDのコメントを編集する。
    コメントの作成者のみが編集可能。
    家族スコープでのアクセス制御により、自分の家族の写真のコメントのみ編集可能。
    削除済みコメント（is_deleted=1）は編集不可。

    Args:
        comment_id: 編集するコメントのID
        update_request: コメント更新リクエスト
        db: データベースセッション
        current_user: 認証済みユーザー情報

    Returns:
        CommentResponse: 更新されたコメント情報

    Raises:
        HTTPException:
            - 404: コメントが見つからない、削除済みコメント、または他家族のコメント
            - 403: コメントの作成者以外がアクセス
            - 422: リクエストボディのバリデーションエラー
            - 500: データベース更新エラー
    """

    # 家族スコープでのコメント取得（削除済みは除外）
    # 写真を経由して家族スコープをチェック
    comment = db.query(Comment).join(Picture, Comment.picture_id == Picture.id).filter(
        and_(
            Comment.id == comment_id,
            Comment.is_deleted == 0,
            Picture.family_id == current_user.family_id
        )
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # コメント作成者のみ編集可能
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")

    # コメント更新処理
    try:
        comment.content = update_request.content
        comment.update_date = datetime.utcnow()

        db.commit()

        # 更新後のコメント情報をユーザー情報と一緒に取得
        updated_comment = db.query(Comment).join(User).filter(Comment.id == comment.id).first()

        logger.info(f"Comment updated: ID={comment_id}, User={current_user.id}")
        return CommentResponse.from_comment(updated_comment)

    except Exception as e:
        logger.error(f"Failed to update comment {comment_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update comment")


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    コメント削除API（論理削除）

    指定されたIDのコメントを論理削除する。
    コメントの作成者のみが削除可能。
    家族スコープでのアクセス制御により、自分の家族の写真のコメントのみ削除可能。
    削除済みコメント（is_deleted=1）は削除不可。

    Args:
        comment_id: 削除するコメントのID
        db: データベースセッション
        current_user: 認証済みユーザー情報

    Returns:
        204 No Content: 削除成功

    Raises:
        HTTPException:
            - 404: コメントが見つからない、削除済みコメント、または他家族のコメント
            - 403: コメントの作成者以外がアクセス
            - 500: データベース更新エラー
    """

    # 家族スコープでのコメント取得（削除済みは除外）
    # 写真を経由して家族スコープをチェック
    comment = db.query(Comment).join(Picture, Comment.picture_id == Picture.id).filter(
        and_(
            Comment.id == comment_id,
            Comment.is_deleted == 0,
            Picture.family_id == current_user.family_id
        )
    ).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # コメント作成者のみ削除可能
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")

    # コメント削除処理（論理削除）
    try:
        comment.is_deleted = 1
        comment.update_date = datetime.utcnow()

        db.commit()
        logger.info(f"Comment deleted: ID={comment_id}, User={current_user.id}")

    except Exception as e:
        logger.error(f"Failed to delete comment {comment_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete comment")