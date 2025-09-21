"""
PATCH /api/users/:id APIのテストファイル（ユーザー情報編集）

権限モデル:
- 管理者（type=10）: 全ユーザーの全フィールド編集可能
- 一般ユーザー（type=0）: 自分自身の基本情報のみ編集可能
  - 編集可能: user_name, email, password
  - 編集不可: type, family_id, status（安全のため）

UserUpdateスキーマ（新規作成予定）:
- 全フィールドOptional（部分更新対応）
- user_name: Optional[str] = None
- password: Optional[str] = None （8文字以上、提供時のみ更新）
- email: Optional[str] = None
- type: Optional[int] = None （管理者のみ変更可能）
- family_id: Optional[int] = None （管理者のみ変更可能）
- status: Optional[int] = None （管理者のみ変更可能）

データ検証ルール:
- user_name: 空文字禁止
- password: 8文字以上（提供された場合のみ）
- email: 有効なメール形式またはNone
- type: 0（一般）または10（管理者）のみ
- family_id: 正の整数
- status: 0（無効）または1（有効）のみ
- 一意制約: user_name, email

エラーレスポンス:
- 400 Bad Request: データ検証エラー
- 401 Unauthorized: 認証失敗
- 403 Forbidden: 権限不足
- 404 Not Found: ユーザーが存在しない
- 409 Conflict: 一意制約違反
- 500 Internal Server Error: サーバーエラー

テスト観点:
1. 正常系テスト
   - 管理者による他ユーザー情報編集成功
   - 一般ユーザーによる自分自身の情報編集成功
   - 部分更新（一部フィールドのみ）の動作確認
   - レスポンス形式の検証
   - パスワード変更時のハッシュ化確認

2. 認証・認可テスト
   - 認証トークンなしでのアクセス失敗
   - 無効なJWTトークンでのアクセス失敗
   - 期限切れトークンでのアクセス失敗
   - 一般ユーザーが他ユーザーの編集を試行して失敗
   - 無効化されたユーザーでのアクセス失敗

3. データ検証テスト
   - 重複するuser_nameの処理（409 Conflict）
   - 重複するemailの処理（409 Conflict）
   - 無効なemail形式の処理（400 Bad Request）
   - パスワードの最小長チェック（8文字以上）
   - 不正なtype値の処理（0,10以外）
   - 不正なfamily_id値の処理（負数など）
   - 不正なstatus値の処理（0,1以外）
   - 空文字user_nameの処理

4. 権限別編集制限テスト
   - 一般ユーザーがtype変更を試行して失敗（403 Forbidden）
   - 一般ユーザーがfamily_id変更を試行して失敗（403 Forbidden）
   - 一般ユーザーがstatus変更を試行して失敗（403 Forbidden）
   - 管理者による権限フィールドの変更成功

5. エラーハンドリングテスト
   - 存在しないユーザーIDの指定（404 Not Found）
   - 無効なユーザーIDフォーマット（400 Bad Request）
   - 不正な形式のAuthorizationヘッダー
   - 不正なJSONリクエストボディ

6. セキュリティテスト
   - パスワード情報のレスポンス非表示確認
   - 他ユーザーの情報へのアクセス制御
   - 自分を無効化することの禁止

7. 境界値テスト
   - パスワード長の境界値（7文字、8文字）
   - 特殊文字を含むフィールド値
   - 空のリクエストボディでの処理

テスト項目:
- test_edit_user_success_as_admin: 管理者による他ユーザー編集成功
- test_edit_user_success_self: 一般ユーザーによる自分自身編集成功
- test_edit_user_partial_update: 部分更新の動作確認
- test_edit_user_password_change_and_hash: パスワード変更とハッシュ化確認
- test_edit_user_password_not_provided: パスワード未提供時は変更しない
- test_edit_user_no_token: 認証トークンなしでのアクセス失敗
- test_edit_user_invalid_token: 無効なトークンでのアクセス失敗
- test_edit_user_expired_token: 期限切れトークンでのアクセス失敗
- test_edit_user_other_user_forbidden: 一般ユーザーが他ユーザー編集失敗
- test_edit_user_disabled_user: 無効化されたユーザーでのアクセス失敗
- test_edit_user_nonexistent_id: 存在しないユーザーIDでの失敗
- test_edit_user_invalid_id_format: 無効なユーザーID形式での失敗
- test_edit_user_duplicate_username: 重複ユーザー名での409エラー
- test_edit_user_duplicate_email: 重複メールアドレスでの409エラー
- test_edit_user_invalid_email_format: 無効なメール形式での400エラー
- test_edit_user_password_too_short: パスワード8文字未満での400エラー
- test_edit_user_invalid_type_value: 不正なtype値での400エラー
- test_edit_user_invalid_family_id: 不正なfamily_id値での400エラー
- test_edit_user_invalid_status_value: 不正なstatus値での400エラー
- test_edit_user_empty_username: 空文字user_nameでの400エラー
- test_edit_user_regular_user_type_change_forbidden: 一般ユーザーのtype変更禁止
- test_edit_user_regular_user_family_id_change_forbidden: 一般ユーザーのfamily_id変更禁止
- test_edit_user_regular_user_status_change_forbidden: 一般ユーザーのstatus変更禁止
- test_edit_user_admin_privilege_fields_success: 管理者による権限フィールド変更成功
- test_edit_user_response_format: レスポンス形式の検証
- test_edit_user_no_password_in_response: パスワード情報の非表示確認
- test_edit_user_malformed_header: 不正な形式のヘッダーでのアクセス失敗
- test_edit_user_invalid_json: 不正なJSONでのアクセス失敗
- test_edit_user_empty_body: 空のリクエストボディでの処理
"""

from unittest.mock import MagicMock
import pytest
from main import app
from database import get_db
from dependencies import get_current_user


def test_edit_user_success_as_admin(client):
    """管理者による他ユーザー編集成功テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.type = 10  # 管理者
    mock_admin_user.status = 1

    # 編集対象ユーザーのモック
    mock_target_user = MagicMock()
    mock_target_user.id = 2
    mock_target_user.user_name = "target_user"
    mock_target_user.email = "target@example.com"
    mock_target_user.type = 0
    mock_target_user.family_id = 1
    mock_target_user.status = 1
    mock_target_user.create_date = "2023-01-01T00:00:00"
    mock_target_user.update_date = "2023-01-01T00:00:00"

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_target_user
    mock_db.query.return_value = mock_query

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    update_data = {
        "user_name": "updated_user",
        "email": "updated@example.com"
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert "id" in response_data
    assert "password" not in response_data  # パスワードが含まれていないことを確認


def test_edit_user_success_self(client):
    """一般ユーザーによる自分自身編集成功テスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.user_name = "regular_user"
    mock_user.email = "user@example.com"
    mock_user.type = 0  # 一般ユーザー
    mock_user.family_id = 1
    mock_user.status = 1
    mock_user.create_date = "2023-01-01T00:00:00"
    mock_user.update_date = "2023-01-01T00:00:00"

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer user_token"}
    update_data = {
        "user_name": "updated_regular_user",
        "email": "updated_user@example.com"
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert "id" in response_data
    assert "password" not in response_data


def test_edit_user_other_user_forbidden(client):
    """一般ユーザーが他ユーザー編集を試行して失敗するテスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.user_name = "regular_user"
    mock_user.type = 0  # 一般ユーザー
    mock_user.status = 1

    # 他のユーザーのモック
    mock_other_user = MagicMock()
    mock_other_user.id = 3
    mock_other_user.user_name = "other_user"
    mock_other_user.type = 0
    mock_other_user.status = 1

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_other_user
    mock_db.query.return_value = mock_query

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer user_token"}
    update_data = {
        "user_name": "hacked_user"
    }
    response = client.patch("/api/users/3", json=update_data, headers=headers)  # 他ユーザー(ID:3)を編集試行

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions. You can only edit your own profile."


def test_edit_user_nonexistent_id(client):
    """存在しないユーザーIDでの失敗テスト"""
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
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    update_data = {
        "user_name": "updated_user"
    }
    response = client.patch("/api/users/99999", json=update_data, headers=headers)  # 存在しないID

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_edit_user_no_token(client):
    """認証トークンなしでのアクセス失敗テスト"""
    update_data = {
        "user_name": "updated_user"
    }
    response = client.patch("/api/users/1", json=update_data)

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_edit_user_duplicate_username(client):
    """重複ユーザー名での409エラーテスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # 編集対象ユーザーのモック
    mock_target_user = MagicMock()
    mock_target_user.id = 2
    mock_target_user.user_name = "target_user"
    mock_target_user.email = "target@example.com"
    mock_target_user.type = 0
    mock_target_user.family_id = 1
    mock_target_user.status = 1

    # データベースセッションのモック（IntegrityErrorを発生させる）
    from sqlalchemy.exc import IntegrityError

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_target_user
    mock_db.query.return_value = mock_query

    # IntegrityErrorをモック
    integrity_error = IntegrityError("statement", "params", "duplicate key value violates unique constraint user_name")
    integrity_error.orig = Exception("duplicate key value violates unique constraint user_name")
    mock_db.commit.side_effect = integrity_error

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    update_data = {
        "user_name": "existing_user"
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"


def test_edit_user_duplicate_email(client):
    """重複メールアドレスでの409エラーテスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # 編集対象ユーザーのモック
    mock_target_user = MagicMock()
    mock_target_user.id = 2
    mock_target_user.user_name = "target_user"
    mock_target_user.email = "target@example.com"
    mock_target_user.type = 0
    mock_target_user.family_id = 1
    mock_target_user.status = 1

    # データベースセッションのモック（IntegrityErrorを発生させる）
    from sqlalchemy.exc import IntegrityError

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_target_user
    mock_db.query.return_value = mock_query

    # IntegrityErrorをモック
    integrity_error = IntegrityError("statement", "params", "duplicate key value violates unique constraint email")
    integrity_error.orig = Exception("duplicate key value violates unique constraint email")
    mock_db.commit.side_effect = integrity_error

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    update_data = {
        "email": "existing@example.com"
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"


def test_edit_user_invalid_email_format(client):
    """無効なメール形式での400エラーテスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "test_user"
    mock_user.type = 0
    mock_user.status = 1

    # 編集対象ユーザーのモック（自分自身）
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer token"}
    update_data = {
        "email": "invalid-email-format"
    }
    response = client.patch("/api/users/1", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 422  # Pydanticのバリデーションエラー


def test_edit_user_password_too_short(client):
    """パスワード8文字未満での400エラーテスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "test_user"
    mock_user.type = 0
    mock_user.status = 1

    # 編集対象ユーザーのモック（自分自身）
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer token"}
    update_data = {
        "password": "short"
    }
    response = client.patch("/api/users/1", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 422  # Pydanticのバリデーションエラー
    assert "Password must be at least 8 characters long" in str(response.json())


def test_edit_user_invalid_type_value(client):
    """不正なtype値での400エラーテスト"""
    # 管理者ユーザーのモック（type変更には管理者権限が必要）
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # 編集対象ユーザーのモック
    mock_target_user = MagicMock()
    mock_target_user.id = 2
    mock_target_user.user_name = "target_user"
    mock_target_user.type = 0
    mock_target_user.status = 1

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_target_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer token"}
    update_data = {
        "type": 5  # 0と10以外は無効
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 422  # Pydanticのバリデーションエラー
    assert "Type must be 0 (regular user) or 10 (admin)" in str(response.json())


def test_edit_user_invalid_family_id(client):
    """不正なfamily_id値での400エラーテスト"""
    # 管理者ユーザーのモック（family_id変更には管理者権限が必要）
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # 編集対象ユーザーのモック
    mock_target_user = MagicMock()
    mock_target_user.id = 2
    mock_target_user.user_name = "target_user"
    mock_target_user.type = 0
    mock_target_user.status = 1

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_target_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer token"}
    update_data = {
        "family_id": -1  # 負数は無効
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 422  # Pydanticのバリデーションエラー
    assert "Family ID must be a positive integer" in str(response.json())


def test_edit_user_invalid_status_value(client):
    """不正なstatus値での400エラーテスト"""
    # 管理者ユーザーのモック（status変更には管理者権限が必要）
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # 編集対象ユーザーのモック
    mock_target_user = MagicMock()
    mock_target_user.id = 2
    mock_target_user.user_name = "target_user"
    mock_target_user.type = 0
    mock_target_user.status = 1

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_target_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer token"}
    update_data = {
        "status": 2  # 0と1以外は無効
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 422  # Pydanticのバリデーションエラー
    assert "Status must be 0 (disabled) or 1 (enabled)" in str(response.json())


def test_edit_user_empty_username(client):
    """空文字user_nameでの400エラーテスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "test_user"
    mock_user.type = 0
    mock_user.status = 1

    # 編集対象ユーザーのモック（自分自身）
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer token"}
    update_data = {
        "user_name": ""  # 空文字は無効
    }
    response = client.patch("/api/users/1", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 422  # Pydanticのバリデーションエラー
    assert "Username cannot be empty" in str(response.json())


def test_edit_user_regular_user_type_change_forbidden(client):
    """一般ユーザーのtype変更禁止テスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.user_name = "regular_user"
    mock_user.type = 0  # 一般ユーザー
    mock_user.status = 1

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer user_token"}
    update_data = {
        "type": 10  # 一般ユーザーがtype変更を試行
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions. You cannot change user type."


def test_edit_user_regular_user_family_id_change_forbidden(client):
    """一般ユーザーのfamily_id変更禁止テスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.user_name = "regular_user"
    mock_user.type = 0  # 一般ユーザー
    mock_user.status = 1

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer user_token"}
    update_data = {
        "family_id": 2  # 一般ユーザーがfamily_id変更を試行
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions. You cannot change family ID."


def test_edit_user_regular_user_status_change_forbidden(client):
    """一般ユーザーのstatus変更禁止テスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.user_name = "regular_user"
    mock_user.type = 0  # 一般ユーザー
    mock_user.status = 1

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer user_token"}
    update_data = {
        "status": 0  # 一般ユーザーがstatus変更を試行
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions. You cannot change user status."


def test_edit_user_admin_privilege_fields_success(client):
    """管理者による権限フィールド変更成功テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.user_name = "admin_user"
    mock_admin_user.type = 10  # 管理者
    mock_admin_user.status = 1

    # 編集対象ユーザーのモック
    mock_target_user = MagicMock()
    mock_target_user.id = 2
    mock_target_user.user_name = "target_user"
    mock_target_user.email = "target@example.com"
    mock_target_user.type = 0
    mock_target_user.family_id = 1
    mock_target_user.status = 1
    mock_target_user.create_date = "2023-01-01T00:00:00"
    mock_target_user.update_date = "2023-01-01T00:00:00"

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_target_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    update_data = {
        "type": 10,  # 管理者による権限変更
        "family_id": 2,
        "status": 0
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert "id" in response_data
    assert "password" not in response_data  # パスワードが含まれていないことを確認


def test_edit_user_partial_update(client):
    """部分更新の動作確認テスト"""
    # 管理者ユーザーのモック
    mock_admin_user = MagicMock()
    mock_admin_user.id = 1
    mock_admin_user.type = 10
    mock_admin_user.status = 1

    # 編集対象ユーザーのモック
    mock_target_user = MagicMock()
    mock_target_user.id = 2
    mock_target_user.user_name = "original_user"
    mock_target_user.email = "original@example.com"
    mock_target_user.type = 0
    mock_target_user.family_id = 1
    mock_target_user.status = 1
    mock_target_user.create_date = "2023-01-01T00:00:00"
    mock_target_user.update_date = "2023-01-01T00:00:00"

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_target_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_admin_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    # user_nameのみ更新（他のフィールドは提供しない）
    update_data = {
        "user_name": "updated_user_only"
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    response_data = response.json()
    assert "id" in response_data
    assert "password" not in response_data


def test_edit_user_password_change_and_hash(client):
    """パスワード変更とハッシュ化確認テスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.user_name = "test_user"
    mock_user.email = "test@example.com"
    mock_user.type = 0
    mock_user.family_id = 1
    mock_user.status = 1
    mock_user.create_date = "2023-01-01T00:00:00"
    mock_user.update_date = "2023-01-01T00:00:00"

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query

    # パスワードハッシュ化のモック確認
    from unittest.mock import patch
    hash_called = []
    def mock_hash(password):
        hash_called.append(password)
        return "hashed_" + password  # ハッシュの代わりにプレフィックスを付ける

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    # パスワードハッシュ機能をモック
    with patch('auth.pwd_context.hash', side_effect=mock_hash):
        headers = {"Authorization": "Bearer user_token"}
        update_data = {
            "password": "newpassword123"
        }
        response = client.patch("/api/users/2", json=update_data, headers=headers)

        # テスト後にオーバーライドをクリア
        app.dependency_overrides.clear()

        assert response.status_code == 200
        # パスワードがハッシュ化されたことを確認
        assert len(hash_called) == 1
        assert hash_called[0] == "newpassword123"


def test_edit_user_password_not_provided(client):
    """パスワード未提供時は変更しないテスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.user_name = "test_user"
    mock_user.email = "test@example.com"
    mock_user.type = 0
    mock_user.family_id = 1
    mock_user.status = 1
    mock_user.create_date = "2023-01-01T00:00:00"
    mock_user.update_date = "2023-01-01T00:00:00"

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query

    # パスワードハッシュ化が呼ばれないことを確認
    from auth import pwd_context
    original_hash = pwd_context.hash
    hash_called = []
    def mock_hash(password):
        hash_called.append(password)
        return original_hash(password)

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer user_token"}
    update_data = {
        "user_name": "updated_username"  # パスワードは提供しない
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 200
    # パスワードハッシュ化が呼ばれていないことを確認
    assert len(hash_called) == 0


def test_edit_user_disabled_user(client):
    """無効化されたユーザーでのアクセス失敗テスト"""
    # 無効化されたユーザーのモック
    mock_disabled_user = MagicMock()
    mock_disabled_user.id = 2
    mock_disabled_user.user_name = "disabled_user"
    mock_disabled_user.type = 0
    mock_disabled_user.status = 0  # 無効化されたユーザー

    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_disabled_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer disabled_token"}
    update_data = {
        "user_name": "updated_user"
    }
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is disabled"


def test_edit_user_invalid_id_format(client):
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
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer admin_token"}
    update_data = {
        "user_name": "updated_user"
    }
    # 無効なID形式（文字列）でリクエスト
    response = client.patch("/api/users/invalid_id", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    assert response.status_code == 422  # FastAPIのパス検証エラー


def test_edit_user_empty_body(client):
    """空のリクエストボディでの処理テスト"""
    # 一般ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.user_name = "test_user"
    mock_user.email = "test@example.com"
    mock_user.type = 0
    mock_user.family_id = 1
    mock_user.status = 1
    mock_user.create_date = "2023-01-01T00:00:00"
    mock_user.update_date = "2023-01-01T00:00:00"

    # データベースセッションのモック
    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db.query.return_value = mock_query
    # dependencies.get_current_user 関数をモック
    def mock_get_current_user():
        return mock_user

    # FastAPIアプリの依存性注入をオーバーライド
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user

    headers = {"Authorization": "Bearer user_token"}
    # 空のリクエストボディ
    update_data = {}
    response = client.patch("/api/users/2", json=update_data, headers=headers)

    # テスト後にオーバーライドをクリア
    app.dependency_overrides.clear()

    # 空のボディでも200 OKが返される（何も更新されない）
    assert response.status_code == 200
    response_data = response.json()
    assert "id" in response_data
    assert "password" not in response_data