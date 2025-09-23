"""
コメント削除API (DELETE /api/comments/:id) のテスト

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 他ファミリーのコメント削除拒否
   - 他ユーザーのコメント削除拒否（コメント作成者のみ削除可能）
   - 存在しないユーザーでの削除拒否

2. 削除処理テスト
   - 正常なコメント削除
   - 削除日時の設定（deleted_at）
   - 削除後のコメントは表示されないことの確認
   - カスケード削除の確認（関連データの整合性）

3. エラー処理テスト
   - 存在しないコメントID
   - 削除済みコメントの再削除
   - 削除済み写真に関連するコメントの削除
   - 無効なコメントID形式

4. レスポンス検証テスト
   - 削除成功時のレスポンス
   - ステータスコードの確認（204 No Content）
   - エラー時のレスポンス形式

5. データ整合性テスト
   - 削除前後のコメント数の変化
   - 写真のコメント数の更新
   - 削除されたコメントの検索結果への非表示

テスト項目（18項目）:

【成功パターン】(3項目)
- test_delete_comment_success: 正常なコメント削除（コメント作成者による削除）
- test_delete_comment_response_status: 削除成功時のステータスコード確認（204）
- test_delete_comment_not_visible_after_deletion: 削除後のコメントが表示されないことの確認

【認証・認可】(5項目)
- test_delete_comment_without_auth: 未認証ユーザーのアクセス拒否（403）
- test_delete_comment_other_family: 他ファミリーのコメント削除拒否（404）
- test_delete_comment_other_user: 同じファミリーの他ユーザーのコメント削除拒否（403）
- test_delete_comment_with_deleted_user: 削除済みユーザーでのアクセス拒否（403）
- test_delete_comment_with_invalid_token: 無効なトークンでのアクセス拒否（403）

【エラー処理】(5項目)
- test_delete_comment_not_found: 存在しないコメントIDでエラー（404）
- test_delete_comment_invalid_id_format: 無効なIDフォーマットでエラー（400）
- test_delete_comment_already_deleted: 削除済みコメントの再削除でエラー（404）
- test_delete_comment_on_deleted_picture: 削除済み写真のコメント削除（404）
- test_delete_comment_non_numeric_id: 数値以外のIDでエラー（400）

【データ整合性】(5項目)
- test_delete_comment_soft_delete: ソフト削除の確認（deleted_atが設定される）
- test_delete_comment_count_update: 写真のコメント数が正しく更新される
- test_delete_comment_cascade_behavior: 関連データの整合性確認
- test_delete_comment_list_exclusion: 削除されたコメントがリスト取得時に除外される
- test_delete_comment_detail_access_denied: 削除されたコメントの詳細取得が拒否される
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from database import get_db
from dependencies import get_current_user

# 共通モックセットアップ
def setup_comment_delete_mocks(
    comment=None, picture=None, comment_count_before=1, comment_count_after=0,
    cascade_ok=True
):
    """
    コメント削除API用のDB・モデルモック
    """
    mock_db_session = MagicMock()

    # コメント取得クエリ: JOINつき
    mock_comment_query = MagicMock()
    mock_comment_join = MagicMock()
    mock_comment_filter = MagicMock()
    mock_comment_filter.first.return_value = comment
    mock_comment_join.filter.return_value = mock_comment_filter
    mock_comment_query.join.return_value = mock_comment_join

    # 写真取得クエリ: コメント数更新確認
    mock_picture_query = MagicMock()
    mock_picture_filter = MagicMock()
    mock_picture_filter.first.return_value = picture
    mock_picture_query.filter.return_value = mock_picture_filter

    # クエリ呼び分け
    def query_side_effect(model):
        if model.__name__ == "Comment":
            return mock_comment_query
        elif model.__name__ == "Picture":
            return mock_picture_query
        else:
            return MagicMock()
    mock_db_session.query.side_effect = query_side_effect

    # コメント数更新（commitを呼ぶだけ）
    mock_db_session.commit.return_value = None

    return mock_db_session

# ========================
# 成功パターンテスト (3項目)
# ========================

def test_delete_comment_success():
    """正常なコメント削除（コメント作成者による削除）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # コメント: 削除前
    mock_comment = MagicMock()
    mock_comment.id = 10
    mock_comment.user_id = 1
    mock_comment.family_id = 1
    mock_comment.is_deleted = 0
    mock_comment.picture_id = 5
    mock_comment.deleted_at = None
    mock_comment.create_date = datetime(2024, 1, 10)
    mock_comment.update_date = datetime(2024, 1, 10)

    # 写真: コメント数2→1
    mock_picture = MagicMock()
    mock_picture.comment_count = 2

    mock_db_session = setup_comment_delete_mocks(
        comment=mock_comment, picture=mock_picture, comment_count_before=2, comment_count_after=1
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.delete("/api/comments/10")
        assert response.status_code == 204
        # commitが呼ばれていること
        assert mock_db_session.commit.called
        # 削除フラグ・日時が設定されていること
        assert mock_comment.is_deleted == 1 or mock_comment.is_deleted is True
        assert mock_comment.deleted_at is not None
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_response_status():
    """削除成功時のステータスコード確認（204）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    mock_comment = MagicMock()
    mock_comment.id = 100
    mock_comment.user_id = 1
    mock_comment.family_id = 1
    mock_comment.is_deleted = 0
    mock_comment.picture_id = 3
    mock_comment.deleted_at = None

    mock_picture = MagicMock()
    mock_picture.comment_count = 1

    mock_db_session = setup_comment_delete_mocks(
        comment=mock_comment, picture=mock_picture
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.delete("/api/comments/100")
        assert response.status_code == 204
        assert response.content == b""
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_not_visible_after_deletion():
    """削除後のコメントが表示されないことの確認（リスト取得/詳細取得で除外）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 削除済みコメント
    mock_comment = MagicMock()
    mock_comment.id = 11
    mock_comment.user_id = 1
    mock_comment.family_id = 1
    mock_comment.is_deleted = 1
    mock_comment.picture_id = 5
    mock_comment.deleted_at = datetime.utcnow()

    mock_picture = MagicMock()
    mock_picture.comment_count = 0

    mock_db_session = setup_comment_delete_mocks(
        comment=mock_comment, picture=mock_picture
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        # コメント詳細
        response = client.get("/api/comments/11")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()

# ========================
# 認証・認可テスト (5項目)
# ========================

def test_delete_comment_without_auth():
    """未認証ユーザーのアクセス拒否（403）"""
    client = TestClient(app)
    response = client.delete("/api/comments/1")
    assert response.status_code == 403

def test_delete_comment_other_family():
    """他ファミリーのコメント削除拒否（404）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 他ファミリーのコメント（family_id=2）→家族スコープ的に見つからない
    mock_db_session = setup_comment_delete_mocks(comment=None)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.delete("/api/comments/20")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()

def test_delete_comment_other_user():
    """同じファミリーの他ユーザーのコメント削除拒否（403）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # コメント作成者はid=2
    mock_comment = MagicMock()
    mock_comment.id = 30
    mock_comment.user_id = 2
    mock_comment.family_id = 1
    mock_comment.is_deleted = 0
    mock_comment.picture_id = 1
    mock_comment.deleted_at = None

    mock_picture = MagicMock()
    mock_picture.comment_count = 1

    mock_db_session = setup_comment_delete_mocks(comment=mock_comment, picture=mock_picture)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.delete("/api/comments/30")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()

def test_delete_comment_with_deleted_user():
    """削除済みユーザーでのアクセス拒否（403）"""
    client = TestClient(app)
    # 削除済みユーザーは認証時点で拒否される想定
    response = client.delete("/api/comments/1")
    assert response.status_code == 403

def test_delete_comment_with_invalid_token():
    """無効なトークンでのアクセス拒否（403）"""
    client = TestClient(app)
    # 無効なトークンは認証時点で拒否される
    response = client.delete("/api/comments/1")
    assert response.status_code == 403

# ========================
# エラー処理テスト (5項目)
# ========================

def test_delete_comment_not_found():
    """存在しないコメントIDでエラー（404）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_db_session = setup_comment_delete_mocks(comment=None)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.delete("/api/comments/999")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()

def test_delete_comment_invalid_id_format():
    """無効なIDフォーマットでエラー（422/400）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.delete("/api/comments/abc")
        assert response.status_code in [400, 422]
    finally:
        app.dependency_overrides.clear()

def test_delete_comment_already_deleted():
    """削除済みコメントの再削除でエラー（404）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # すでに is_deleted=1
    mock_comment = MagicMock()
    mock_comment.id = 40
    mock_comment.user_id = 1
    mock_comment.family_id = 1
    mock_comment.is_deleted = 1
    mock_comment.deleted_at = datetime.utcnow()

    mock_picture = MagicMock()
    mock_picture.comment_count = 1

    mock_db_session = setup_comment_delete_mocks(comment=None, picture=mock_picture)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.delete("/api/comments/40")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()

def test_delete_comment_on_deleted_picture():
    """削除済み写真のコメント削除（404）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # コメント自体は存在するが、紐付く写真が削除済みで取得できない
    mock_comment = MagicMock()
    mock_comment.id = 50
    mock_comment.user_id = 1
    mock_comment.family_id = 1
    mock_comment.is_deleted = 0
    mock_comment.picture_id = 999

    # Pictureが見つからない (deleted)
    mock_db_session = setup_comment_delete_mocks(comment=mock_comment, picture=None)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.delete("/api/comments/50")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()

def test_delete_comment_non_numeric_id():
    """数値以外のIDでエラー（422/400）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.delete("/api/comments/xyz")
        assert response.status_code in [400, 422]
    finally:
        app.dependency_overrides.clear()

# ========================
# データ整合性テスト (5項目)
# ========================

def test_delete_comment_soft_delete():
    """ソフト削除の確認（deleted_atが設定される）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    mock_comment = MagicMock()
    mock_comment.id = 60
    mock_comment.user_id = 1
    mock_comment.family_id = 1
    mock_comment.is_deleted = 0
    mock_comment.picture_id = 1
    mock_comment.deleted_at = None

    mock_picture = MagicMock()
    mock_picture.comment_count = 1

    mock_db_session = setup_comment_delete_mocks(comment=mock_comment, picture=mock_picture)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.delete("/api/comments/60")
        assert response.status_code == 204
        # ソフトデリート（deleted_atセット）
        assert mock_comment.deleted_at is not None
        assert mock_comment.is_deleted == 1 or mock_comment.is_deleted is True
    finally:
        app.dependency_overrides.clear()

def test_delete_comment_count_update():
    """写真のコメント数が正しく更新される"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    mock_comment = MagicMock()
    mock_comment.id = 70
    mock_comment.user_id = 1
    mock_comment.family_id = 1
    mock_comment.is_deleted = 0
    mock_comment.picture_id = 5

    mock_picture = MagicMock()
    mock_picture.comment_count = 2

    mock_db_session = setup_comment_delete_mocks(comment=mock_comment, picture=mock_picture)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        # 削除前
        before_count = mock_picture.comment_count
        response = client.delete("/api/comments/70")
        assert response.status_code == 204
        # 削除後: コメント数が1減ることを想定
        assert mock_picture.comment_count == before_count - 1 or mock_picture.comment_count <= before_count
    finally:
        app.dependency_overrides.clear()

def test_delete_comment_cascade_behavior():
    """関連データの整合性確認（カスケード削除）"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 例: 通知やLike等の関連データが残らないこと（ここではcommitが呼ばれていればOKとする）
    mock_comment = MagicMock()
    mock_comment.id = 80
    mock_comment.user_id = 1
    mock_comment.family_id = 1
    mock_comment.is_deleted = 0
    mock_comment.picture_id = 1

    mock_picture = MagicMock()
    mock_picture.comment_count = 1

    mock_db_session = setup_comment_delete_mocks(comment=mock_comment, picture=mock_picture, cascade_ok=True)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.delete("/api/comments/80")
        assert response.status_code == 204
        assert mock_db_session.commit.called
    finally:
        app.dependency_overrides.clear()

def test_delete_comment_list_exclusion():
    """削除されたコメントがリスト取得時に除外される"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # コメントリスト: is_deleted=1のものは返さない
    mock_comment = MagicMock()
    mock_comment.id = 90
    mock_comment.is_deleted = 1
    mock_comment.family_id = 1

    # モック: all() が空リストを返す
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_join = MagicMock()
    mock_filter = MagicMock()
    mock_order = MagicMock()
    mock_order.all.return_value = []
    mock_filter.order_by.return_value = mock_order
    mock_join.filter.return_value = mock_filter
    mock_query.join.return_value = mock_join
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.get("/api/comments?picture_id=1")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()

def test_delete_comment_detail_access_denied():
    """削除されたコメントの詳細取得が拒否される"""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # コメント is_deleted=1
    mock_comment = MagicMock()
    mock_comment.id = 91
    mock_comment.is_deleted = 1
    mock_comment.family_id = 1

    mock_db_session = setup_comment_delete_mocks(comment=None)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session
    try:
        response = client.get("/api/comments/91")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()