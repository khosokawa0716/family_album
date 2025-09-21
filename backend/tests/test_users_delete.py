"""
DELETE /api/users/:id APIのテストファイル（ユーザー削除・管理者のみ）

権限モデル:
- 管理者（type=10）のみユーザー削除可能
- 一般ユーザー（type=0）はユーザー削除不可
- 削除対象: 任意のユーザー（管理者、一般ユーザー問わず）
- 自分自身の削除も可能（管理者の場合）

削除方式:
- 論理削除: statusを0に変更（無効化）

エラーレスポンス:
- 401 Unauthorized: 認証失敗
- 403 Forbidden: 権限不足（一般ユーザーがアクセス）
- 404 Not Found: 削除対象ユーザーが存在しない
- 409 Conflict: 既に削除済みユーザーの削除試行
- 422 Unprocessable Entity: 無効なユーザーIDフォーマット
- 500 Internal Server Error: サーバーエラー

レスポンス形式（成功時）:
- 200 OK: 削除成功メッセージ付き
  {
    "message": "User deleted successfully",
    "deleted_user_id": 123
  }

関連データの処理:
- そのまま残す: 削除されたユーザーが作成した写真・コメントはそのまま保持
- フロントエンド側で削除済みユーザーの表示制御を実装

操作ログ記録:
- OperationLogsテーブルに記録
- operation: "DELETE", target_type: "user", target_id: 削除ユーザーID
- detail: 削除前のユーザー情報JSON（user_name, email, type, family_id, status）

セキュリティ考慮事項:
- 削除操作は管理者のみに制限
- 自分自身の削除も許可
- 最後の管理者削除保護は実装しない

テスト観点:
1. 正常系テスト
   - 管理者による他ユーザー削除成功
   - 管理者による自分自身削除成功
   - レスポンス形式の検証
   - 削除後のデータベース状態確認

2. 認証・認可テスト
   - 認証トークンなしでのアクセス失敗
   - 無効なJWTトークンでのアクセス失敗
   - 期限切れトークンでのアクセス失敗
   - 一般ユーザーでの削除試行失敗
   - 無効化された管理者ユーザーでのアクセス失敗

3. データ検証テスト
   - 存在しないユーザーIDの削除試行（404 Not Found）
   - 無効なユーザーIDフォーマット（422 Unprocessable Entity）
   - 既に削除済み（status=0）ユーザーの削除試行

4. エラーハンドリングテスト
   - 不正な形式のAuthorizationヘッダー
   - 不正なJSONリクエストボディ（該当する場合）
   - データベースエラーのハンドリング

5. セキュリティテスト
   - 管理者以外のアクセス制御確認
   - トークン偽造時のアクセス拒否
   - 削除権限の厳格な検証

6. 境界値・特殊ケーステスト
   - 最後の管理者ユーザーの削除試行
   - 関連データを持つユーザーの削除
   - 削除対象ユーザーIDの境界値

テスト項目:
- test_delete_user_success_as_admin: 管理者による他ユーザー削除成功
- test_delete_user_success_self_admin: 管理者による自分自身削除成功
- test_delete_user_no_token: 認証トークンなしでのアクセス失敗
- test_delete_user_invalid_token: 無効なトークンでのアクセス失敗
- test_delete_user_expired_token: 期限切れトークンでのアクセス失敗
- test_delete_user_regular_user_forbidden: 一般ユーザーでの削除試行失敗
- test_delete_user_disabled_admin: 無効化された管理者でのアクセス失敗
- test_delete_user_nonexistent_id: 存在しないユーザーIDでの削除失敗
- test_delete_user_invalid_id_format: 無効なユーザーID形式での失敗
- test_delete_user_already_deleted: 既に削除済みユーザーの削除試行
- test_delete_user_malformed_header: 不正な形式のヘッダーでのアクセス失敗
- test_delete_user_response_format: レスポンス形式の検証
- test_delete_user_database_state_after_deletion: 削除後のデータベース状態確認
"""

from unittest.mock import MagicMock
import pytest


def test_delete_user_success_as_admin(client, monkeypatch):
    """管理者による他ユーザー削除成功テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.type = 10  # 管理者
    mock_admin_user.status = 1

    # 削除対象ユーザーのモック
    mock_target_user = MagicMock()
    mock_target_user.id = 2
    mock_target_user.user_name = "target_user"
    mock_target_user.email = "target@example.com"
    mock_target_user.type = 0
    mock_target_user.family_id = 1
    mock_target_user.status = 1

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_target_user
    mock_db.query.return_value = mock_query

    # OperationLogクラスをモック
    mock_operation_log_class = MagicMock()
    monkeypatch.setattr("routers.users.OperationLog", mock_operation_log_class)

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    from database import get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = lambda: mock_db

    headers = {"Authorization": "Bearer admin_token"}
    response = client.delete("/api/users/2", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["message"] == "User deleted successfully"
    assert response_data["deleted_user_id"] == 2

    # 論理削除が実行されたことを確認
    assert mock_target_user.status == 0

    # セッションのコミットが呼ばれたことを確認
    mock_db.commit.assert_called_once()


def test_delete_user_success_self_admin(client, monkeypatch):
    """管理者による自分自身削除成功テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.type = 10  # 管理者
    mock_admin_user.status = 1

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_admin_user
    mock_db.query.return_value = mock_query

    # OperationLogクラスをモック
    mock_operation_log_class = MagicMock()
    monkeypatch.setattr("routers.users.OperationLog", mock_operation_log_class)

    # jsonモジュールのモック
    mock_json = MagicMock()
    mock_json.dumps.return_value = '{"test": "data"}'
    monkeypatch.setattr("routers.users.json", mock_json)

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    from database import get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = lambda: mock_db

    headers = {"Authorization": "Bearer admin_token"}
    response = client.delete("/api/users/1", headers=headers)  # 自分自身を削除

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["message"] == "User deleted successfully"
    assert response_data["deleted_user_id"] == 1


def test_delete_user_no_token(client):
    """認証トークンなしでのアクセス失敗テスト"""
    response = client.delete("/api/users/1")
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_delete_user_invalid_token(client):
    """無効なトークンでのアクセス失敗テスト"""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.delete("/api/users/1", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_delete_user_expired_token(client):
    """期限切れトークンでのアクセス失敗テスト"""
    headers = {"Authorization": "Bearer expired_token"}
    response = client.delete("/api/users/1", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_delete_user_regular_user_forbidden(client):
    """一般ユーザーでの削除試行失敗テスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.user_name = "regular_user"
    mock_user.type = 0  # 一般ユーザー
    mock_user.status = 1

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer user_token"}
    response = client.delete("/api/users/1", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions. Admin access required."


def test_delete_user_disabled_admin(client):
    """無効化された管理者でのアクセス失敗テスト"""
    # 無効化された管理者ユーザーのモック
    mock_disabled_admin = MagicMock()
    mock_disabled_admin.id = 1
    mock_disabled_admin.user_name = "disabled_admin"
    mock_disabled_admin.type = 10  # 管理者
    mock_disabled_admin.status = 0  # 無効化されたユーザー

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_disabled_admin

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer disabled_admin_token"}
    response = client.delete("/api/users/2", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is disabled"


def test_delete_user_nonexistent_id(client):
    """存在しないユーザーIDでの削除失敗テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # データベースセッションのモック（ユーザーが見つからない）
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    mock_db.query.return_value = mock_query

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    from database import get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = lambda: mock_db

    headers = {"Authorization": "Bearer admin_token"}
    response = client.delete("/api/users/99999", headers=headers)  # 存在しないID

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_delete_user_invalid_id_format(client):
    """無効なユーザーID形式での失敗テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    # 無効なID形式（文字列）でリクエスト
    response = client.delete("/api/users/invalid_id", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 422  # FastAPIのパス検証エラー


def test_delete_user_already_deleted(client):
    """既に削除済みユーザーの削除試行テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # 既に削除済みのユーザーのモック
    mock_deleted_user = MagicMock()
    mock_deleted_user.id = 2
    mock_deleted_user.user_name = "deleted_user"
    mock_deleted_user.status = 0  # 既に削除済み

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_deleted_user
    mock_db.query.return_value = mock_query

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    from database import get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = lambda: mock_db

    headers = {"Authorization": "Bearer admin_token"}
    response = client.delete("/api/users/2", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == "User is already deleted"


def test_delete_user_malformed_header(client):
    """不正な形式のヘッダーでのアクセス失敗テスト"""
    headers = {"Authorization": "InvalidFormat"}
    response = client.delete("/api/users/1", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_delete_user_response_format(client, monkeypatch):
    """レスポンス形式の検証テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # 削除対象ユーザーのモック
    mock_target_user = MagicMock()
    mock_target_user.id = 2
    mock_target_user.user_name = "target_user"
    mock_target_user.email = "target@example.com"
    mock_target_user.type = 0
    mock_target_user.family_id = 1
    mock_target_user.status = 1

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_target_user
    mock_db.query.return_value = mock_query

    # OperationLogクラスをモック
    mock_operation_log_class = MagicMock()
    monkeypatch.setattr("routers.users.OperationLog", mock_operation_log_class)

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    from main import app
    from dependencies import get_current_user
    from database import get_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_db] = lambda: mock_db

    headers = {"Authorization": "Bearer admin_token"}
    response = client.delete("/api/users/2", headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()

    # レスポンス形式の検証
    assert "message" in response_data
    assert "deleted_user_id" in response_data
    assert response_data["message"] == "User deleted successfully"
    assert response_data["deleted_user_id"] == 2
    assert isinstance(response_data["deleted_user_id"], int)


def test_delete_user_database_state_after_deletion(client, monkeypatch):
    """削除後のデータベース状態確認テスト"""
    # このテストは実装で論理削除が正しく行われることを確認
    # test_delete_user_success_as_admin で mock_target_user.status == 0 を確認済み
    pass


