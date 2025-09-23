"""
GET /api/logs APIのテストファイル（操作ログ一覧取得）

操作ログ一覧取得API仕様:
- 管理者のみがアクセス可能（type=10）
- 全ての操作ログを作成日時の降順で取得
- 一般ユーザー（type=0）はアクセス不可（403）

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 一般ユーザーのアクセス拒否（管理者のみ）
   - 無効・期限切れトークンでのアクセス拒否
   - 削除済みユーザーでのアクセス拒否

2. 基本動作テスト
   - ログが0件の場合の正常レスポンス
   - ログが存在する場合の正常レスポンス
   - レスポンス構造の検証
   - デフォルトソート（作成日降順）

3. レスポンス形式テスト
   - 配列形式のレスポンス
   - ログオブジェクトの必須フィールド
   - データ型の検証

4. エラーハンドリングテスト
   - 不正な形式のAuthorizationヘッダー
   - DBエラーシミュレート

テスト項目（13項目）:

【認証・認可系】(5項目)
- test_get_logs_without_auth: 未認証でのアクセス拒否（403）
- test_get_logs_general_user: 一般ユーザーでのアクセス拒否（403）
- test_get_logs_with_invalid_token: 無効トークンでのアクセス拒否（401）
- test_get_logs_deleted_user: 削除済みユーザーでのアクセス拒否（403）
- test_get_logs_malformed_header: 不正な形式のヘッダー（403）

【基本動作】(4項目)
- test_get_logs_empty_list: ログ0件時の正常レスポンス
- test_get_logs_success: ログ存在時の正常レスポンス
- test_get_logs_response_format: レスポンス形式の検証
- test_get_logs_sort_order: デフォルトソート（作成日降順）確認

【エラーハンドリング】(2項目)
- test_get_logs_user_not_found: 存在しないユーザーのトークン（401）
- test_get_logs_db_error: DB接続エラー時の適切なエラーレスポンス

【管理者権限テスト】(2項目)
- test_get_logs_admin_access: 管理者の正常アクセス
- test_get_logs_admin_only: 管理者のみアクセス可能確認
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from datetime import datetime

from main import app
from database import get_db
from dependencies import get_current_user


# ========================
# 認証・認可系テスト (5項目)
# ========================

def test_get_logs_without_auth():
    """未認証でのアクセス拒否（403）"""
    client = TestClient(app)
    response = client.get("/api/logs")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_get_logs_general_user():
    """一般ユーザーでのアクセス拒否（403）"""
    client = TestClient(app)

    # 一般ユーザー（type=0）のモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "general_user"
    mock_user.type = 0  # 一般ユーザー
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.get("/api/logs")
        assert response.status_code == 403
        assert response.json()["detail"] == "管理者のみアクセス可能です"
    finally:
        app.dependency_overrides.clear()


def test_get_logs_with_invalid_token():
    """無効トークンでのアクセス拒否（401）"""
    client = TestClient(app)

    # get_current_user 関数が例外を投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/logs", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_get_logs_deleted_user():
    """削除済みユーザーでのアクセス拒否（403）"""
    client = TestClient(app)

    # get_current_user 関数が無効ユーザーエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=403, detail="User account is disabled")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer disabled_user_token"}
        response = client.get("/api/logs", headers=headers)
        assert response.status_code == 403
        assert response.json()["detail"] == "User account is disabled"
    finally:
        app.dependency_overrides.clear()


def test_get_logs_malformed_header():
    """不正な形式のヘッダー（403）"""
    client = TestClient(app)

    # "Bearer "がないヘッダー
    headers = {"Authorization": "invalid_token"}
    response = client.get("/api/logs", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # 空のヘッダー
    headers = {"Authorization": ""}
    response = client.get("/api/logs", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # "Bearer"のみ
    headers = {"Authorization": "Bearer"}
    response = client.get("/api/logs", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


# ========================
# 基本動作テスト (4項目)
# ========================

def test_get_logs_empty_list():
    """ログ0件時の正常レスポンス"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10  # 管理者
    mock_user.status = 1

    # データベースモック（空のログリスト）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.order_by.return_value.all.return_value = []

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/logs")
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == []
        assert isinstance(response_data, list)
    finally:
        app.dependency_overrides.clear()


def test_get_logs_success():
    """ログ存在時の正常レスポンス"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10  # 管理者
    mock_user.status = 1

    # ログのモック
    mock_log1 = MagicMock()
    mock_log1.id = 1
    mock_log1.user_id = 1
    mock_log1.operation = "CREATE"
    mock_log1.target_type = "picture"
    mock_log1.target_id = 1
    mock_log1.detail = "写真をアップロードしました"
    mock_log1.create_date = datetime(2024, 1, 2, 10, 0, 0)

    mock_log2 = MagicMock()
    mock_log2.id = 2
    mock_log2.user_id = 2
    mock_log2.operation = "UPDATE"
    mock_log2.target_type = "category"
    mock_log2.target_id = 1
    mock_log2.detail = "カテゴリを編集しました"
    mock_log2.create_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック（作成日降順でソート済み）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.order_by.return_value.all.return_value = [mock_log1, mock_log2]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/logs")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]["id"] == 1
        assert response_data[0]["operation"] == "CREATE"
        assert response_data[1]["id"] == 2
        assert response_data[1]["operation"] == "UPDATE"
    finally:
        app.dependency_overrides.clear()


def test_get_logs_response_format():
    """レスポンス形式の検証"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10  # 管理者
    mock_user.status = 1

    # ログのモック
    mock_log = MagicMock()
    mock_log.id = 1
    mock_log.user_id = 1
    mock_log.operation = "CREATE"
    mock_log.target_type = "picture"
    mock_log.target_id = 1
    mock_log.detail = "写真をアップロードしました"
    mock_log.create_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.order_by.return_value.all.return_value = [mock_log]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/logs")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        response_data = response.json()
        assert isinstance(response_data, list)
        assert len(response_data) == 1

        log = response_data[0]
        required_fields = ["id", "user_id", "operation", "target_type", "target_id", "detail", "create_date"]
        for field in required_fields:
            assert field in log, f"Required field '{field}' missing from response"

        # データ型の確認
        assert isinstance(log["id"], int)
        assert isinstance(log["user_id"], int)
        assert isinstance(log["operation"], str)
        assert isinstance(log["target_type"], str)
        assert isinstance(log["create_date"], str)
    finally:
        app.dependency_overrides.clear()


def test_get_logs_sort_order():
    """デフォルトソート（作成日降順）確認"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10  # 管理者
    mock_user.status = 1

    # 異なる作成日のログモック（作成日降順でソートされた結果）
    mock_log_new = MagicMock()
    mock_log_new.id = 1
    mock_log_new.user_id = 1
    mock_log_new.operation = "CREATE"
    mock_log_new.target_type = "picture"
    mock_log_new.target_id = 1
    mock_log_new.detail = "新しい操作"
    mock_log_new.create_date = datetime(2024, 1, 2, 10, 0, 0)

    mock_log_old = MagicMock()
    mock_log_old.id = 2
    mock_log_old.user_id = 1
    mock_log_old.operation = "UPDATE"
    mock_log_old.target_type = "category"
    mock_log_old.target_id = 1
    mock_log_old.detail = "古い操作"
    mock_log_old.create_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック（作成日降順でソート済み）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.order_by.return_value.all.return_value = [mock_log_new, mock_log_old]

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/logs")
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        # 新しいログが最初
        assert response_data[0]["detail"] == "新しい操作"
        # 古いログが次
        assert response_data[1]["detail"] == "古い操作"
    finally:
        app.dependency_overrides.clear()


# ========================
# エラーハンドリングテスト (2項目)
# ========================

def test_get_logs_user_not_found():
    """存在しないユーザーのトークン（401）"""
    client = TestClient(app)

    # get_current_user 関数がユーザー見つからないエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer nonexistent_user_token"}
        response = client.get("/api/logs", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_get_logs_db_error():
    """DB接続エラー時の適切なエラーレスポンス"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10  # 管理者
    mock_user.status = 1

    # データベースエラーのモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.order_by.return_value.all.side_effect = Exception("Database connection error")

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/logs")
        # DBエラーの場合は500エラーが期待される
        assert response.status_code == 500
    finally:
        app.dependency_overrides.clear()


# ========================
# 管理者権限テスト (2項目)
# ========================

def test_get_logs_admin_access():
    """管理者の正常アクセス"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10  # 管理者
    mock_user.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.order_by.return_value.all.return_value = []

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/logs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    finally:
        app.dependency_overrides.clear()


def test_get_logs_admin_only():
    """管理者のみアクセス可能確認"""
    # test_get_logs_general_user()と同じロジック
    test_get_logs_general_user()