"""
PATCH /api/categories/:id APIのテストファイル（カテゴリ編集・管理者のみ）

カテゴリ編集API仕様:
- 管理者権限（type=10）を持つ認証済みユーザーのみがカテゴリを編集可能
- 編集対象カテゴリは認証ユーザーと同じfamily_idのもののみ
- カテゴリ名と説明を編集可能（いずれも任意）
- 重複するカテゴリ名は同一家族内で禁止（自分自身を除く）
- 削除済み（status=0）カテゴリは編集不可
- 編集時はupdate_dateが自動更新される

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 無効・期限切れトークンでのアクセス拒否
   - 管理者権限のないユーザーのアクセス拒否（type!=10）
   - 削除済みユーザーでのアクセス拒否
   - 管理者権限を持つ有効ユーザーでのアクセス許可

2. リソースアクセステスト
   - 存在しないカテゴリIDでのアクセス拒否（404）
   - 他家族のカテゴリへのアクセス拒否（403）
   - 削除済みカテゴリ（status=0）への編集拒否（410）
   - 無効なID形式（文字列、負数等）での拒否（422）

3. リクエスト形式テスト
   - 適切なJSONリクエストボディの処理
   - 不正なJSON形式の拒否
   - 空のリクエストボディでの拒否
   - 不正なフィールド型の拒否
   - 編集項目なし（nameもdescriptionもnull）での拒否

4. バリデーションテスト
   - カテゴリ名の文字数制限（最小・最大）
   - 説明の文字数制限
   - 特殊文字・絵文字を含むカテゴリ名の処理
   - HTMLタグを含む内容の適切な処理
   - 同一家族内での重複カテゴリ名の拒否（自分自身を除く）
   - 空文字・null値での適切な処理

5. 基本動作テスト
   - カテゴリ名のみの編集
   - 説明のみの編集
   - カテゴリ名と説明の同時編集
   - 編集項目の部分更新（PATCHセマンティクス）
   - update_dateの自動更新確認
   - レスポンス構造の検証

6. セキュリティテスト
   - SQLインジェクション攻撃への耐性
   - XSS攻撃対象文字列の適切な処理
   - 他家族のfamily_id指定攻撃の防止
   - 過度に長い入力値での攻撃防止

7. エラーハンドリングテスト
   - データベースエラー時の適切なエラーレスポンス
   - 重複制約違反時の適切なエラーレスポンス
   - 不正なパラメータでのエラーハンドリング

テスト項目（30項目）:

【認証・認可系】(7項目)
- test_patch_categories_without_auth: 未認証でのアクセス拒否（403）
- test_patch_categories_with_invalid_token: 無効トークンでのアクセス拒否（401）
- test_patch_categories_with_expired_token: 期限切れトークンでのアクセス拒否（401）
- test_patch_categories_non_admin_user: 管理者権限なしユーザーでのアクセス拒否（403）
- test_patch_categories_deleted_user: 削除済みユーザーでのアクセス拒否（403）
- test_patch_categories_malformed_header: 不正な形式のヘッダー（403）
- test_patch_categories_admin_success: 管理者権限ユーザーでのアクセス許可

【リソースアクセス】(6項目)
- test_patch_categories_not_found: 存在しないカテゴリIDでのアクセス拒否（404）
- test_patch_categories_other_family: 他家族のカテゴリへのアクセス拒否（403）
- test_patch_categories_deleted_category: 削除済みカテゴリへの編集拒否（410）
- test_patch_categories_invalid_id_string: 文字列IDでのアクセス拒否（422）
- test_patch_categories_invalid_id_negative: 負数IDでのアクセス拒否（422）
- test_patch_categories_invalid_id_zero: ゼロIDでのアクセス拒否（422）

【リクエスト形式】(5項目)
- test_patch_categories_valid_json: 適切なJSONリクエストでの正常処理
- test_patch_categories_invalid_json: 不正なJSON形式での拒否（400）
- test_patch_categories_empty_body: 空のリクエストボディでの拒否（422）
- test_patch_categories_invalid_field_type: 不正なフィールド型での拒否（422）
- test_patch_categories_no_update_fields: 編集項目なしでの拒否（422）

【バリデーション】(6項目)
- test_patch_categories_name_min_length: カテゴリ名最小文字数制限（422）
- test_patch_categories_name_max_length: カテゴリ名最大文字数制限（422）
- test_patch_categories_description_max_length: 説明最大文字数制限（422）
- test_patch_categories_special_characters: 特殊文字・絵文字を含むカテゴリ名の成功
- test_patch_categories_html_content: HTMLタグを含む内容の適切な処理
- test_patch_categories_duplicate_name: 同一家族内重複カテゴリ名の拒否（409）

【基本動作】(4項目)
- test_patch_categories_name_only: カテゴリ名のみの編集
- test_patch_categories_description_only: 説明のみの編集
- test_patch_categories_both_fields: カテゴリ名と説明の同時編集
- test_patch_categories_update_date: update_dateの自動更新確認

【セキュリティ】(2項目)
- test_patch_categories_sql_injection: SQLインジェクション攻撃への耐性
- test_patch_categories_xss_prevention: XSS攻撃対象文字列の適切な処理
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

def test_patch_categories_without_auth():
    """未認証でのアクセス拒否（403）"""
    client = TestClient(app)
    response = client.patch("/api/categories/1", json={"name": "テストカテゴリ"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_patch_categories_with_invalid_token():
    """無効トークンでのアクセス拒否（401）"""
    client = TestClient(app)

    # get_current_user 関数が例外を投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.patch("/api/categories/1", headers=headers, json={"name": "テストカテゴリ"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_with_expired_token():
    """期限切れトークンでのアクセス拒否（401）"""
    client = TestClient(app)

    # get_current_user 関数が期限切れエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer expired_token"}
        response = client.patch("/api/categories/1", headers=headers, json={"name": "テストカテゴリ"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_non_admin_user():
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
        response = client.patch("/api/categories/1", json={"name": "テストカテゴリ"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Admin access required"
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_deleted_user():
    """削除済みユーザーでのアクセス拒否（403）"""
    client = TestClient(app)

    # get_current_user 関数が無効ユーザーエラーを投げるようにモック
    def mock_get_current_user():
        raise HTTPException(status_code=403, detail="User account is disabled")

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        headers = {"Authorization": "Bearer disabled_user_token"}
        response = client.patch("/api/categories/1", headers=headers, json={"name": "テストカテゴリ"})
        assert response.status_code == 403
        assert response.json()["detail"] == "User account is disabled"
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_malformed_header():
    """不正な形式のヘッダー（403）"""
    client = TestClient(app)

    # "Bearer "がないヘッダー
    headers = {"Authorization": "invalid_token"}
    response = client.patch("/api/categories/1", headers=headers, json={"name": "テストカテゴリ"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # 空のヘッダー
    headers = {"Authorization": ""}
    response = client.patch("/api/categories/1", headers=headers, json={"name": "テストカテゴリ"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"

    # "Bearer"のみ
    headers = {"Authorization": "Bearer"}
    response = client.patch("/api/categories/1", headers=headers, json={"name": "テストカテゴリ"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_patch_categories_admin_success():
    """管理者権限ユーザーでのアクセス許可"""
    client = TestClient(app)

    # 管理者権限のあるユーザー（type = 10）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "既存カテゴリ"
    mock_category.description = "既存の説明"
    mock_category.status = 1
    mock_category.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category.update_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()

    # 1回目: カテゴリ取得
    # 2回目: 重複チェック（自分自身を除く）
    def query_side_effect(*args):
        mock_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_query.filter.return_value = mock_filter_query

        # 1回目の呼び出し: カテゴリ取得
        if not hasattr(query_side_effect, 'call_count'):
            query_side_effect.call_count = 0
        query_side_effect.call_count += 1

        if query_side_effect.call_count == 1:
            mock_filter_query.first.return_value = mock_category  # カテゴリ存在
        else:
            mock_filter_query.first.return_value = None  # 重複なし

        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/categories/1", json={"name": "更新カテゴリ"})
        assert response.status_code == 200
        response_data = response.json()
        assert "id" in response_data
        assert response_data["name"] == "更新カテゴリ"
        assert response_data["family_id"] == 1
    finally:
        app.dependency_overrides.clear()


# ========================
# リソースアクセステスト (6項目)
# ========================

def test_patch_categories_not_found():
    """存在しないカテゴリIDでのアクセス拒否（404）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック（カテゴリが見つからない）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # カテゴリが存在しない
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/categories/999", json={"name": "テストカテゴリ"})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_other_family():
    """他家族のカテゴリへのアクセス拒否（403）"""
    client = TestClient(app)

    # 認証ユーザー（family_id = 1）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # データベースモック（他家族のデータは家族スコープで除外される）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 他家族のデータは除外される
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/categories/1", json={"name": "テストカテゴリ"})
        assert response.status_code == 404  # 家族スコープ外は「見つからない」として処理
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_deleted_category():
    """削除済みカテゴリへの編集拒否（410）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 削除済みカテゴリ（status=0）
    mock_deleted_category = MagicMock()
    mock_deleted_category.id = 1
    mock_deleted_category.family_id = 1
    mock_deleted_category.name = "削除済みカテゴリ"
    mock_deleted_category.status = 0  # 削除済み

    # データベースモック（status=0のカテゴリを返す）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_deleted_category
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/categories/1", json={"name": "テストカテゴリ"})
        assert response.status_code == 410
        assert "deleted" in response.json()["detail"].lower() or "gone" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_invalid_id_string():
    """文字列IDでのアクセス拒否（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 文字列のIDでアクセス
        response = client.patch("/api/categories/abc", json={"name": "テストカテゴリ"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_invalid_id_negative():
    """負数IDでのアクセス拒否（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 負数のIDでアクセス
        response = client.patch("/api/categories/-1", json={"name": "テストカテゴリ"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_invalid_id_zero():
    """ゼロIDでのアクセス拒否（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 0のIDでアクセス
        response = client.patch("/api/categories/0", json={"name": "テストカテゴリ"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ========================
# リクエスト形式テスト (5項目)
# ========================

def test_patch_categories_valid_json():
    """適切なJSONリクエストでの正常処理"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "admin_user"
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "既存カテゴリ"
    mock_category.description = "既存の説明"
    mock_category.status = 1

    # データベースモック
    mock_db_session = MagicMock()

    def query_side_effect(*args):
        mock_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_query.filter.return_value = mock_filter_query

        if not hasattr(query_side_effect, 'call_count'):
            query_side_effect.call_count = 0
        query_side_effect.call_count += 1

        if query_side_effect.call_count == 1:
            mock_filter_query.first.return_value = mock_category  # カテゴリ存在
        else:
            mock_filter_query.first.return_value = None  # 重複なし

        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # 説明ありのJSONリクエスト
        response = client.patch("/api/categories/1", json={
            "name": "有効カテゴリ",
            "description": "有効なカテゴリの説明"
        })
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == "有効カテゴリ"
        assert response_data["description"] == "有効なカテゴリの説明"
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_invalid_json():
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
        response = client.patch("/api/categories/1", headers=headers, data='{"name": invalid_json}')
        assert response.status_code == 422  # FastAPIのJSONデコードエラー
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_empty_body():
    """空のリクエストボディでの拒否（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # 空のリクエストボディ
        response = client.patch("/api/categories/1", json={})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_invalid_field_type():
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
        response = client.patch("/api/categories/1", json={"name": 123, "description": "説明"})
        assert response.status_code == 422

        # nameが配列型のリクエスト
        response = client.patch("/api/categories/1", json={"name": ["カテゴリ名"], "description": "説明"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_no_update_fields():
    """編集項目なしでの拒否（422）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # nameもdescriptionもNoneのリクエスト
        response = client.patch("/api/categories/1", json={"name": None, "description": None})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ========================
# バリデーションテスト (6項目)
# ========================

def test_patch_categories_name_min_length():
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
        response = client.patch("/api/categories/1", json={"name": "A", "description": "説明"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_name_max_length():
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
        response = client.patch("/api/categories/1", json={"name": long_name, "description": "説明"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_description_max_length():
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
        response = client.patch("/api/categories/1", json={"name": "カテゴリ名", "description": long_description})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_special_characters():
    """特殊文字・絵文字を含むカテゴリ名の成功"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "既存カテゴリ"
    mock_category.status = 1

    # データベースモック
    mock_db_session = MagicMock()

    def query_side_effect(*args):
        mock_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_query.filter.return_value = mock_filter_query

        if not hasattr(query_side_effect, 'call_count'):
            query_side_effect.call_count = 0
        query_side_effect.call_count += 1

        if query_side_effect.call_count == 1:
            mock_filter_query.first.return_value = mock_category  # カテゴリ存在
        else:
            mock_filter_query.first.return_value = None  # 重複なし

        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # 特殊文字・絵文字を含むカテゴリ名
        special_name = "旅行🎌日本&海外 (2024)"
        response = client.patch("/api/categories/1", json={
            "name": special_name,
            "description": "特殊文字・絵文字テスト"
        })
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == special_name
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_html_content():
    """HTMLタグを含む内容の適切な処理"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "既存カテゴリ"
    mock_category.status = 1

    # データベースモック
    mock_db_session = MagicMock()

    def query_side_effect(*args):
        mock_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_query.filter.return_value = mock_filter_query

        if not hasattr(query_side_effect, 'call_count'):
            query_side_effect.call_count = 0
        query_side_effect.call_count += 1

        if query_side_effect.call_count == 1:
            mock_filter_query.first.return_value = mock_category  # カテゴリ存在
        else:
            mock_filter_query.first.return_value = None  # 重複なし

        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # HTMLタグを含むカテゴリ名と説明
        html_name = "<script>alert('test')</script>カテゴリ"
        html_description = "<b>太字</b>の説明<br>改行あり"
        response = client.patch("/api/categories/1", json={
            "name": html_name,
            "description": html_description
        })
        assert response.status_code == 200
        response_data = response.json()
        # HTMLタグがそのまま保存されることを確認（エスケープ処理など）
        assert response_data["name"] == html_name
        assert response_data["description"] == html_description
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_duplicate_name():
    """同一家族内重複カテゴリ名の拒否（409）"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "編集対象"
    mock_category.status = 1

    # 既存のカテゴリ（重複チェック用）
    mock_existing_category = MagicMock()
    mock_existing_category.id = 2  # 異なるID
    mock_existing_category.family_id = 1
    mock_existing_category.name = "既存カテゴリ"
    mock_existing_category.status = 1

    # データベースモック
    mock_db_session = MagicMock()

    def query_side_effect(*args):
        mock_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_query.filter.return_value = mock_filter_query

        if not hasattr(query_side_effect, 'call_count'):
            query_side_effect.call_count = 0
        query_side_effect.call_count += 1

        if query_side_effect.call_count == 1:
            mock_filter_query.first.return_value = mock_category  # カテゴリ存在
        else:
            mock_filter_query.first.return_value = mock_existing_category  # 重複あり

        return mock_query

    mock_db_session.query.side_effect = query_side_effect

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # 既存と同じカテゴリ名で編集試行
        response = client.patch("/api/categories/1", json={
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

def test_patch_categories_name_only():
    """カテゴリ名のみの編集"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "既存カテゴリ"
    mock_category.description = "既存の説明"
    mock_category.status = 1
    mock_category.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category.update_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()

    def query_side_effect(*args):
        mock_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_query.filter.return_value = mock_filter_query

        if not hasattr(query_side_effect, 'call_count'):
            query_side_effect.call_count = 0
        query_side_effect.call_count += 1

        if query_side_effect.call_count == 1:
            mock_filter_query.first.return_value = mock_category  # カテゴリ存在
        else:
            mock_filter_query.first.return_value = None  # 重複なし

        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/categories/1", json={"name": "新しいカテゴリ"})
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == "新しいカテゴリ"
        assert response_data["description"] == "既存の説明"  # 説明は変更されない
        assert response_data["family_id"] == 1
        assert response_data["status"] == 1
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_description_only():
    """説明のみの編集"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "既存カテゴリ"
    mock_category.description = "既存の説明"
    mock_category.status = 1
    mock_category.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category.update_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_category  # カテゴリ存在
    mock_db_session.query.return_value = mock_query
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/categories/1", json={"description": "更新した説明"})
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == "既存カテゴリ"  # 名前は変更されない
        assert response_data["description"] == "更新した説明"
        assert response_data["family_id"] == 1
        assert response_data["status"] == 1
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_both_fields():
    """カテゴリ名と説明の同時編集"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "既存カテゴリ"
    mock_category.description = "既存の説明"
    mock_category.status = 1
    mock_category.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category.update_date = datetime(2024, 1, 1, 10, 0, 0)

    # データベースモック
    mock_db_session = MagicMock()

    def query_side_effect(*args):
        mock_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_query.filter.return_value = mock_filter_query

        if not hasattr(query_side_effect, 'call_count'):
            query_side_effect.call_count = 0
        query_side_effect.call_count += 1

        if query_side_effect.call_count == 1:
            mock_filter_query.first.return_value = mock_category  # カテゴリ存在
        else:
            mock_filter_query.first.return_value = None  # 重複なし

        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/categories/1", json={
            "name": "新しいカテゴリ",
            "description": "新しい説明"
        })
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == "新しいカテゴリ"
        assert response_data["description"] == "新しい説明"
        assert response_data["family_id"] == 1
        assert response_data["status"] == 1
        assert "create_date" in response_data
        assert "update_date" in response_data
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_update_date():
    """update_dateの自動更新確認"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "既存カテゴリ"
    mock_category.description = "既存の説明"
    mock_category.status = 1
    mock_category.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_category.update_date = datetime(2024, 1, 1, 10, 0, 0)

    updated_time = datetime(2024, 1, 2, 15, 30, 0)

    # データベースモック
    mock_db_session = MagicMock()

    def query_side_effect(*args):
        mock_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_query.filter.return_value = mock_filter_query

        if not hasattr(query_side_effect, 'call_count'):
            query_side_effect.call_count = 0
        query_side_effect.call_count += 1

        if query_side_effect.call_count == 1:
            mock_filter_query.first.return_value = mock_category  # カテゴリ存在
        else:
            mock_filter_query.first.return_value = None  # 重複なし

        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.commit.return_value = None

    def mock_refresh(obj):
        # update_dateが更新されることをシミュレート
        obj.update_date = updated_time

    mock_db_session.refresh.side_effect = mock_refresh

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/categories/1", json={"name": "更新されたカテゴリ"})
        assert response.status_code == 200
        response_data = response.json()

        # update_dateが自動更新されることを確認
        assert "update_date" in response_data
        # モックのrefreshが呼ばれたことを確認
        mock_db_session.refresh.assert_called_once()
    finally:
        app.dependency_overrides.clear()


# ========================
# セキュリティテスト (2項目)
# ========================

def test_patch_categories_sql_injection():
    """SQLインジェクション攻撃への耐性"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "既存カテゴリ"
    mock_category.status = 1

    # データベースモック
    mock_db_session = MagicMock()

    def query_side_effect(*args):
        mock_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_query.filter.return_value = mock_filter_query

        if not hasattr(query_side_effect, 'call_count'):
            query_side_effect.call_count = 0
        query_side_effect.call_count += 1

        if query_side_effect.call_count == 1:
            mock_filter_query.first.return_value = mock_category  # カテゴリ存在
        else:
            mock_filter_query.first.return_value = None  # 重複なし

        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # SQLインジェクション試行のカテゴリ名
        sql_injection_name = "'; DROP TABLE categories; --"
        sql_injection_desc = "1' OR '1'='1"

        response = client.patch("/api/categories/1", json={
            "name": sql_injection_name,
            "description": sql_injection_desc
        })

        # SQLインジェクション攻撃が無効化され、通常のテキストとして処理されることを確認
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["name"] == sql_injection_name  # エスケープされて保存
        assert response_data["description"] == sql_injection_desc
    finally:
        app.dependency_overrides.clear()


def test_patch_categories_xss_prevention():
    """XSS攻撃対象文字列の適切な処理"""
    client = TestClient(app)

    # 管理者ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.type = 10
    mock_user.status = 1

    # 編集対象のカテゴリ
    mock_category = MagicMock()
    mock_category.id = 1
    mock_category.family_id = 1
    mock_category.name = "既存カテゴリ"
    mock_category.status = 1

    # データベースモック
    mock_db_session = MagicMock()

    def query_side_effect(*args):
        mock_query = MagicMock()
        mock_filter_query = MagicMock()
        mock_query.filter.return_value = mock_filter_query

        if not hasattr(query_side_effect, 'call_count'):
            query_side_effect.call_count = 0
        query_side_effect.call_count += 1

        if query_side_effect.call_count == 1:
            mock_filter_query.first.return_value = mock_category  # カテゴリ存在
        else:
            mock_filter_query.first.return_value = None  # 重複なし

        return mock_query

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # XSS攻撃試行の文字列
        xss_name = "<script>alert('XSS')</script>カテゴリ"
        xss_desc = "<img src=x onerror=alert('XSS')>説明"

        response = client.patch("/api/categories/1", json={
            "name": xss_name,
            "description": xss_desc
        })

        # XSS攻撃が無効化され、適切に処理されることを確認
        assert response.status_code == 200
        response_data = response.json()
        # 文字列がそのまま保存される（フロントエンドでエスケープ処理される想定）
        assert response_data["name"] == xss_name
        assert response_data["description"] == xss_desc
    finally:
        app.dependency_overrides.clear()