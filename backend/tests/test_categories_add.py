"""
POST /api/categories APIのテストファイル（カテゴリ追加・管理者のみ）

カテゴリ追加API仕様:
- 管理者権限（type=10）を持つ認証済みユーザーのみがカテゴリを追加可能
- family_idは認証ユーザーの家族IDが自動設定される
- カテゴリ名は必須、説明は任意
- 重複するカテゴリ名は同一家族内で禁止
- 新規作成時はstatus=1（有効）で自動設定

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 無効・期限切れトークンでのアクセス拒否
   - 管理者権限のないユーザーのアクセス拒否（type!=10）
   - 削除済みユーザーでのアクセス拒否
   - 管理者権限を持つ有効ユーザーでのアクセス許可

2. リクエスト形式テスト
   - 適切なJSONリクエストボディの処理
   - 不正なJSON形式の拒否
   - 必須フィールド（name）の検証
   - 不正なフィールド型の拒否
   - 空文字・null値での拒否

3. バリデーションテスト
   - カテゴリ名の文字数制限（最小・最大）
   - 説明の文字数制限
   - 特殊文字・絵文字を含むカテゴリ名の処理
   - HTMLタグを含む内容の適切な処理
   - 同一家族内での重複カテゴリ名の拒否

4. 基本動作テスト
   - 有効なカテゴリの正常登録
   - 自動設定項目の確認（family_id, status, 作成日時）
   - 説明なしカテゴリの正常登録
   - レスポンス構造の検証

5. セキュリティテスト
   - SQLインジェクション攻撃への耐性
   - XSS攻撃対象文字列の適切な処理
   - 他家族のfamily_id指定攻撃の防止
   - 過度に長い入力値での攻撃防止

6. エラーハンドリングテスト
   - データベースエラー時の適切なエラーレスポンス
   - 重複制約違反時の適切なエラーレスポンス
   - 不正なパラメータでのエラーハンドリング

テスト項目（25項目）:

【認証・認可系】(7項目)
- test_post_categories_without_auth: 未認証でのアクセス拒否（403）
- test_post_categories_with_invalid_token: 無効トークンでのアクセス拒否（401）
- test_post_categories_with_expired_token: 期限切れトークンでのアクセス拒否（401）
- test_post_categories_non_admin_user: 管理者権限なしユーザーでのアクセス拒否（403）
- test_post_categories_deleted_user: 削除済みユーザーでのアクセス拒否（403）
- test_post_categories_malformed_header: 不正な形式のヘッダー（403）
- test_post_categories_admin_success: 管理者権限ユーザーでのアクセス許可

【リクエスト形式】(6項目)
- test_post_categories_valid_json: 適切なJSONリクエストでの正常処理
- test_post_categories_invalid_json: 不正なJSON形式での拒否（400）
- test_post_categories_missing_name: 必須フィールド（name）なしでの拒否（422）
- test_post_categories_invalid_field_type: 不正なフィールド型での拒否（422）
- test_post_categories_empty_name: 空文字カテゴリ名での拒否（422）
- test_post_categories_null_name: null値カテゴリ名での拒否（422）

【バリデーション】(6項目)
- test_post_categories_name_min_length: カテゴリ名最小文字数制限（422）
- test_post_categories_name_max_length: カテゴリ名最大文字数制限（422）
- test_post_categories_description_max_length: 説明最大文字数制限（422）
- test_post_categories_special_characters: 特殊文字・絵文字を含むカテゴリ名の成功
- test_post_categories_html_content: HTMLタグを含む内容の適切な処理
- test_post_categories_duplicate_name: 同一家族内重複カテゴリ名の拒否（409）

【基本動作】(4項目)
- test_post_categories_success_with_description: 説明ありカテゴリの正常登録
- test_post_categories_success_without_description: 説明なしカテゴリの正常登録
- test_post_categories_auto_fields: 自動設定フィールドの確認（family_id, status, 日時）
- test_post_categories_response_format: レスポンス形式の検証

【セキュリティ】(2項目)
- test_post_categories_sql_injection: SQLインジェクション攻撃への耐性
- test_post_categories_xss_prevention: XSS攻撃対象文字列の適切な処理
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from datetime import datetime

from main import app
from database import get_db
from dependencies import get_current_user


# ========================
# 認証・認可系テスト (7項目)
# ========================

def test_post_categories_without_auth():
    """未認証でのアクセス拒否（403）"""
    client = TestClient(app)
    response = client.post("/api/categories", json={"name": "テストカテゴリ"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_post_categories_with_invalid_token():
    """無効トークンでのアクセス拒否（401）"""
    client = TestClient(app)

    # get_current_user 関数が例外を投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/api/categories", headers=headers, json={"name": "テストカテゴリ"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_post_categories_with_expired_token():
    """期限切れトークンでのアクセス拒否（401）"""
    client = TestClient(app)

    # get_current_user 関数が期限切れエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer expired_token"}
        response = client.post("/api/categories", headers=headers, json={"name": "テストカテゴリ"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_post_categories_non_admin_user():
    """管理者権限なしユーザーでのアクセス拒否（403）"""
    client = TestClient(app)

    # 管理者権限のないユーザー（type != 10）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"
    mock_user.type = 0  # 一般ユーザー
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.post("/api/categories", json={"name": "テストカテゴリ"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Admin access required"
    finally:
        app.dependency_overrides.clear()


def test_post_categories_deleted_user():
    """削除済みユーザーでのアクセス拒否（403）"""
    client = TestClient(app)

    # get_current_user 関数が無効ユーザーエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=403, detail="User account is disabled")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer disabled_user_token"}
        response = client.post("/api/categories", headers=headers, json={"name": "テストカテゴリ"})
        assert response.status_code == 403
        assert response.json()["detail"] == "User account is disabled"
    finally:
        app.dependency_overrides.clear()


def test_post_categories_malformed_header():
    """不正な形式のヘッダー（403）"""
    client = TestClient(app)

    # "Bearer "がないヘッダー
    headers = {"Authorization": "invalid_token"}
    response = client.post("/api/categories", headers=headers, json={"name": "テストカテゴリ"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # 空のヘッダー
    headers = {"Authorization": ""}
    response = client.post("/api/categories", headers=headers, json={"name": "テストカテゴリ"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # "Bearer"のみ
    headers = {"Authorization": "Bearer"}
    response = client.post("/api/categories", headers=headers, json={"name": "テストカテゴリ"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_post_categories_admin_success():
    """管理者権限ユーザーでのアクセス許可"""
    client = TestClient(app)

    # 管理者権限のあるユーザー（type = 10）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10
    mock_user.status = 1

    # 作成されたカテゴリのモック
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "新規カテゴリ"
    mock_category.description = None
    mock_category.status = 1
    mock_category.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category.update_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック（重複チェック用）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 重複なし
    mock_db_session.query.return_value = mock_query
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    # refreshで更新されるカテゴリのIDを設定
    def mock_refresh(obj):
        obj.id = 1
        obj.create_date = datetime(2024, 1, 1, 10, 0, 0)
        obj.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.post("/api/categories", json={"name": "新規カテゴリ"})
        assert response.status_code == 201
        response_data = response.json()
        assert "id" in response_data
        assert response_data["name"] == "新規カテゴリ"
        assert response_data["family_id"] == 1
        assert response_data["status"] == 1
    finally:
        app.dependency_overrides.clear()


# ========================
# リクエスト形式テスト (6項目)
# ========================

def test_post_categories_valid_json():
    """適切なJSONリクエストでの正常処理"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 重複なし
    mock_db_session.query.return_value = mock_query
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    def mock_refresh(obj):
        obj.id = 1
        obj.create_date = datetime(2024, 1, 1, 10, 0, 0)
        obj.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # 説明ありのJSONリクエスト
        response = client.post("/api/categories", json={
            "name": "有効カテゴリ",
            "description": "有効なカテゴリの説明"
        })
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["name"] == "有効カテゴリ"
        assert response_data["description"] == "有効なカテゴリの説明"
    finally:
        app.dependency_overrides.clear()


def test_post_categories_invalid_json():
    """不正なJSON形式での拒否（400）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 不正なJSON形式のリクエスト
        headers = {"Content-Type": "application/json"}
        response = client.post("/api/categories", headers=headers, content='{"name": invalid_json}')
        assert response.status_code == 422  # FastAPIのJSONデコードエラー
    finally:
        app.dependency_overrides.clear()


def test_post_categories_missing_name():
    """必須フィールド（name）なしでの拒否（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # nameフィールドなしのリクエスト
        response = client.post("/api/categories", json={"description": "説明のみ"})
        assert response.status_code == 422
        assert "name" in str(response.json())
    finally:
        app.dependency_overrides.clear()


def test_post_categories_invalid_field_type():
    """不正なフィールド型での拒否（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # nameが数値型のリクエスト
        response = client.post("/api/categories", json={"name": 123, "description": "説明"})
        assert response.status_code == 422

        # nameが配列型のリクエスト
        response = client.post("/api/categories", json={"name": ["カテゴリ名"], "description": "説明"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_post_categories_empty_name():
    """空文字カテゴリ名での拒否（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 空文字のnameのリクエスト
        response = client.post("/api/categories", json={"name": "", "description": "説明"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_post_categories_null_name():
    """null値カテゴリ名での拒否（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # null値のnameのリクエスト
        response = client.post("/api/categories", json={"name": None, "description": "説明"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ========================
# バリデーションテスト (6項目)
# ========================

def test_post_categories_name_min_length():
    """カテゴリ名最小文字数制限（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 最小文字数未満のカテゴリ名（1文字）
        response = client.post("/api/categories", json={"name": "A", "description": "説明"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_post_categories_name_max_length():
    """カテゴリ名最大文字数制限（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 最大文字数超過のカテゴリ名（例：51文字）
        long_name = "A" * 51
        response = client.post("/api/categories", json={"name": long_name, "description": "説明"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_post_categories_description_max_length():
    """説明最大文字数制限（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 最大文字数超過の説明（例：501文字）
        long_description = "A" * 501
        response = client.post("/api/categories", json={"name": "カテゴリ名", "description": long_description})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_post_categories_special_characters():
    """特殊文字・絵文字を含むカテゴリ名の成功"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 重複なし
    mock_db_session.query.return_value = mock_query
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    def mock_refresh(obj):
        obj.id = 1
        obj.create_date = datetime(2024, 1, 1, 10, 0, 0)
        obj.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # 特殊文字・絵文字を含むカテゴリ名
        special_name = "旅行🎌日本&海外 (2024)"
        response = client.post("/api/categories", json={
            "name": special_name,
            "description": "特殊文字・絵文字テスト"
        })
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["name"] == special_name
    finally:
        app.dependency_overrides.clear()


def test_post_categories_html_content():
    """HTMLタグを含む内容の適切な処理"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 重複なし
    mock_db_session.query.return_value = mock_query
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    def mock_refresh(obj):
        obj.id = 1
        obj.create_date = datetime(2024, 1, 1, 10, 0, 0)
        obj.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # HTMLタグを含むカテゴリ名と説明
        html_name = "<script>alert('test')</script>カテゴリ"
        html_description = "<b>太字</b>の説明<br>改行あり"
        response = client.post("/api/categories", json={
            "name": html_name,
            "description": html_description
        })
        assert response.status_code == 201
        response_data = response.json()
        # HTMLタグがそのまま保存されることを確認（エスケープ処理など）
        assert response_data["name"] == html_name
        assert response_data["description"] == html_description
    finally:
        app.dependency_overrides.clear()


def test_post_categories_duplicate_name():
    """同一家族内重複カテゴリ名の拒否（409）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 既存のカテゴリ（重複チェック用）
    mock_existing_category = MagicMock()
    mock_existing_category.id = 1
    mock_existing_category.family_id = 1
    mock_existing_category.name = "既存カテゴリ"
    mock_existing_category.status = 1

    # データベースモック（重複ありの場合）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_existing_category  # 重複あり
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # 既存と同じカテゴリ名で登録試行
        response = client.post("/api/categories", json={
            "name": "既存カテゴリ",
            "description": "重複チェックテスト"
        })
        assert response.status_code == 409
        assert "already exists in this family" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ========================
# 基本動作テスト (4項目)
# ========================

def test_post_categories_success_with_description():
    """説明ありカテゴリの正常登録"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 重複なし
    mock_db_session.query.return_value = mock_query
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    def mock_refresh(obj):
        obj.id = 1
        obj.family_id = 1
        obj.name = "新しいカテゴリ"
        obj.description = "詳細な説明"
        obj.status = 1
        obj.create_date = datetime(2024, 1, 1, 10, 0, 0)
        obj.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.post("/api/categories", json={
            "name": "新しいカテゴリ",
            "description": "詳細な説明"
        })
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["name"] == "新しいカテゴリ"
        assert response_data["description"] == "詳細な説明"
        assert response_data["family_id"] == 1
        assert response_data["status"] == 1
        assert "create_date" in response_data
        assert "update_date" in response_data
    finally:
        app.dependency_overrides.clear()


def test_post_categories_success_without_description():
    """説明なしカテゴリの正常登録"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 重複なし
    mock_db_session.query.return_value = mock_query
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    def mock_refresh(obj):
        obj.id = 2
        obj.family_id = 1
        obj.name = "シンプルカテゴリ"
        obj.description = None
        obj.status = 1
        obj.create_date = datetime(2024, 1, 1, 10, 0, 0)
        obj.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.post("/api/categories", json={"name": "シンプルカテゴリ"})
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["name"] == "シンプルカテゴリ"
        assert response_data["description"] is None
        assert response_data["family_id"] == 1
        assert response_data["status"] == 1
    finally:
        app.dependency_overrides.clear()


def test_post_categories_auto_fields():
    """自動設定フィールドの確認（family_id, status, 日時）"""
    client = TestClient(app)

    # 管理者ユーザーのモック（family_id = 2）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 2
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 重複なし
    mock_db_session.query.return_value = mock_query
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    created_time = datetime(2024, 1, 1, 10, 0, 0)

    def mock_refresh(obj):
        # ユーザーのfamily_idが自動設定されることを確認
        obj.id = 3
        obj.family_id = 2  # ユーザーのfamily_idが設定される
        obj.name = "自動設定テスト"
        obj.description = "フィールド自動設定のテスト"
        obj.status = 1  # 自動で有効状態
        obj.create_date = created_time
        obj.update_date = created_time

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.post("/api/categories", json={
            "name": "自動設定テスト",
            "description": "フィールド自動設定のテスト"
        })
        assert response.status_code == 201
        response_data = response.json()

        # 自動設定フィールドの確認
        assert response_data["family_id"] == 2  # ユーザーのfamily_idが設定
        assert response_data["status"] == 1  # 自動で有効状態
        assert "create_date" in response_data  # 作成日時が自動設定
        assert "update_date" in response_data  # 更新日時が自動設定
        assert "id" in response_data  # IDが自動採番
    finally:
        app.dependency_overrides.clear()


def test_post_categories_response_format():
    """レスポンス形式の検証"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 重複なし
    mock_db_session.query.return_value = mock_query
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    def mock_refresh(obj):
        obj.id = 4
        obj.family_id = 1
        obj.name = "レスポンステスト"
        obj.description = "レスポンス形式のテスト"
        obj.status = 1
        obj.create_date = datetime(2024, 1, 1, 10, 0, 0)
        obj.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.post("/api/categories", json={
            "name": "レスポンステスト",
            "description": "レスポンス形式のテスト"
        })
        assert response.status_code == 201
        assert response.headers["content-type"] == "application/json"

        response_data = response.json()

        # 必須フィールドの存在確認
        required_fields = ["id", "family_id", "name", "description", "status", "create_date", "update_date"]
        for field in required_fields:
            assert field in response_data, f"Required field '{field}' missing from response"

        # データ型の確認
        assert isinstance(response_data["id"], int)
        assert isinstance(response_data["family_id"], int)
        assert isinstance(response_data["name"], str)
        assert isinstance(response_data["status"], int)
        assert isinstance(response_data["create_date"], str)
        assert isinstance(response_data["update_date"], str)
        # descriptionはstr or None
        assert response_data["description"] is None or isinstance(response_data["description"], str)
    finally:
        app.dependency_overrides.clear()


# ========================
# セキュリティテスト (2項目)
# ========================

def test_post_categories_sql_injection():
    """SQLインジェクション攻撃への耐性"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 重複なし
    mock_db_session.query.return_value = mock_query
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    def mock_refresh(obj):
        obj.id = 5
        obj.family_id = 1
        obj.status = 1
        obj.create_date = datetime(2024, 1, 1, 10, 0, 0)
        obj.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # SQLインジェクション試行のカテゴリ名
        sql_injection_name = "'; DROP TABLE categories; --"
        sql_injection_desc = "1' OR '1'='1"

        response = client.post("/api/categories", json={
            "name": sql_injection_name,
            "description": sql_injection_desc
        })

        # SQLインジェクション攻撃が無効化され、通常のテキストとして処理されることを確認
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["name"] == sql_injection_name  # エスケープされて保存
        assert response_data["description"] == sql_injection_desc
    finally:
        app.dependency_overrides.clear()


def test_post_categories_xss_prevention():
    """XSS攻撃対象文字列の適切な処理"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 重複なし
    mock_db_session.query.return_value = mock_query
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    def mock_refresh(obj):
        obj.id = 6
        obj.family_id = 1
        obj.status = 1
        obj.create_date = datetime(2024, 1, 1, 10, 0, 0)
        obj.update_date = datetime(2024, 1, 1, 10, 0, 0)

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # XSS攻撃試行の文字列
        xss_name = "<script>alert('XSS')</script>カテゴリ"
        xss_desc = "<img src=x onerror=alert('XSS')>説明"

        response = client.post("/api/categories", json={
            "name": xss_name,
            "description": xss_desc
        })

        # XSS攻撃が無効化され、適切に処理されることを確認
        assert response.status_code == 201
        response_data = response.json()
        # 文字列がそのまま保存される（フロントエンドでエスケープ処理される想定）
        assert response_data["name"] == xss_name
        assert response_data["description"] == xss_desc
    finally:
        app.dependency_overrides.clear()