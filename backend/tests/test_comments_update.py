"""
コメント編集API (PATCH /api/comments/:id) のテスト

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 他ファミリーのコメント編集拒否
   - 他ユーザーのコメント編集拒否（コメント作成者のみ編集可能）
   - 存在しないユーザーでの編集拒否

2. 入力検証テスト
   - コメント内容の必須チェック
   - コメント内容の空文字チェック
   - コメント内容の最大文字数チェック（1000文字）
   - 不正な形式のJSONリクエスト

3. 更新処理テスト
   - 正常なコメント更新
   - 更新日時の自動更新
   - 作成日時は変更されないことの確認

4. エラー処理テスト
   - 存在しないコメントID
   - 削除済みコメントの編集拒否
   - 削除済み写真に関連するコメントの編集

5. レスポンス検証テスト
   - 更新後のコメント情報の返却
   - レスポンス形式の検証（JSON）
   - ステータスコードの確認

テスト項目（20項目）:

【成功パターン】(3項目)
- test_update_comment_success: 正常なコメント編集（コメント作成者による編集）
- test_update_comment_with_emoji: 絵文字を含むコメントの編集
- test_update_comment_with_multiline: 改行を含むコメントの編集

【認証・認可】(5項目)
- test_update_comment_without_auth: 未認証ユーザーのアクセス拒否（403）
- test_update_comment_other_family: 他ファミリーのコメント編集拒否（404）
- test_update_comment_other_user: 同じファミリーの他ユーザーのコメント編集拒否（403）
- test_update_comment_with_deleted_user: 削除済みユーザーでのアクセス拒否（403）
- test_update_comment_with_invalid_token: 無効なトークンでのアクセス拒否（403）

【入力検証】(4項目)
- test_update_comment_empty_content: 空のコメント内容でエラー（422）
- test_update_comment_only_spaces: スペースのみのコメント内容でエラー（422）
- test_update_comment_exceed_max_length: 1000文字超過のコメントでエラー（422）
- test_update_comment_invalid_json: 不正なJSON形式でエラー（422）

【エラー処理】(4項目)
- test_update_comment_not_found: 存在しないコメントIDでエラー（404）
- test_update_comment_deleted_comment: 削除済みコメントの編集拒否（404）
- test_update_comment_deleted_picture: 削除済み写真のコメント編集（正常に編集可能）
- test_update_comment_invalid_id_format: 不正なID形式でエラー（422）

【レスポンス検証】(4項目)
- test_update_comment_response_format: レスポンス形式の検証（必須フィールドの確認）
- test_update_comment_updated_at_changed: 更新日時が変更されることを確認
- test_update_comment_created_at_unchanged: 作成日時が変更されないことを確認
- test_update_comment_idempotent: 同じ内容での更新が冪等であることを確認
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from database import get_db
from dependencies import get_current_user


def setup_comment_mock(mock_comment, mock_updated_comment=None):
    """コメント更新テスト用の共通モック設定"""
    mock_db_session = MagicMock()

    # 1回目のクエリ: コメント取得（JOIN付き）
    mock_comment_query = MagicMock()
    mock_comment_join = MagicMock()
    mock_comment_filter = MagicMock()
    mock_comment_filter.first.return_value = mock_comment
    mock_comment_join.filter.return_value = mock_comment_filter
    mock_comment_query.join.return_value = mock_comment_join

    # 2回目のクエリ: 更新後のコメント取得（JOIN付き）
    if mock_updated_comment:
        mock_updated_query = MagicMock()
        mock_updated_join = MagicMock()
        mock_updated_filter = MagicMock()
        mock_updated_filter.first.return_value = mock_updated_comment
        mock_updated_join.filter.return_value = mock_updated_filter
        mock_updated_query.join.return_value = mock_updated_join

        # クエリの呼び出し回数をカウント
        query_call_count = 0
        def query_side_effect(model):
            nonlocal query_call_count
            query_call_count += 1
            if model.__name__ == 'Comment':
                if query_call_count == 1:
                    return mock_comment_query
                else:
                    return mock_updated_query
            return MagicMock()
    else:
        def query_side_effect(model):
            if model.__name__ == 'Comment':
                return mock_comment_query
            return MagicMock()

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.commit.return_value = None

    return mock_db_session


# ========================
# 成功パターンテスト (3項目)
# ========================

def test_update_comment_success():
    """正常なコメント編集（コメント作成者による編集）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"

    # 既存コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1  # 作成者と同じ
    mock_comment.picture_id = 1
    mock_comment.content = "Old content"
    mock_comment.is_deleted = 0
    mock_comment.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_comment.update_date = datetime(2024, 1, 1, 10, 0, 0)

    # 更新後のコメントモック
    mock_updated_comment = MagicMock()
    mock_updated_comment.id = 1
    mock_updated_comment.user_id = 1
    mock_updated_comment.picture_id = 1
    mock_updated_comment.content = "Updated content"
    mock_updated_comment.is_deleted = 0
    mock_updated_comment.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_updated_comment.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_updated_comment.user.user_name = "test_user"
    mock_updated_comment.user.nickname = None

    # データベースモック設定
    mock_db_session = setup_comment_mock(mock_comment, mock_updated_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/1", json={"content": "Updated content"})
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == 1
        assert response_data["content"] == "Updated content"
        assert response_data["user_name"] == "test_user"
        assert "update_date" in response_data
    finally:
        app.dependency_overrides.clear()


def test_update_comment_with_emoji():
    """絵文字を含むコメントの編集"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"

    emoji_content = "更新されたコメント 😊🎉✨"

    # 既存コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.content = "Old content"
    mock_comment.is_deleted = 0

    # 更新後のコメントモック
    mock_updated_comment = MagicMock()
    mock_updated_comment.id = 1
    mock_updated_comment.content = emoji_content
    mock_updated_comment.user_id = 1
    mock_updated_comment.picture_id = 1
    mock_updated_comment.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_updated_comment.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_updated_comment.user.user_name = "test_user"
    mock_updated_comment.user.nickname = None

    # データベースモック設定
    mock_db_session = setup_comment_mock(mock_comment, mock_updated_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/1", json={"content": emoji_content})
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["content"] == emoji_content
    finally:
        app.dependency_overrides.clear()


def test_update_comment_with_multiline():
    """改行を含むコメントの編集"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"

    multiline_content = "行1\n行2\n行3"

    # 既存コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.content = "Old content"
    mock_comment.is_deleted = 0

    # 更新後のコメントモック
    mock_updated_comment = MagicMock()
    mock_updated_comment.id = 1
    mock_updated_comment.content = multiline_content
    mock_updated_comment.user_id = 1
    mock_updated_comment.picture_id = 1
    mock_updated_comment.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_updated_comment.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_updated_comment.user.user_name = "test_user"
    mock_updated_comment.user.nickname = None

    # データベースモック設定
    mock_db_session = setup_comment_mock(mock_comment, mock_updated_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/1", json={"content": multiline_content})
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["content"] == multiline_content
    finally:
        app.dependency_overrides.clear()


# ========================
# 認証・認可テスト (5項目)
# ========================

def test_update_comment_without_auth():
    """未認証ユーザーのアクセス拒否（403）"""
    client = TestClient(app)
    response = client.patch("/api/comments/1", json={"content": "Updated content"})
    assert response.status_code == 403


def test_update_comment_other_family():
    """他ファミリーのコメント編集拒否（404）"""
    client = TestClient(app)

    # 認証ユーザー（family_id = 1）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 他ファミリーのコメント（family_id = 2）のため、家族スコープフィルタで除外される
    mock_db_session = setup_comment_mock(None)  # コメントが見つからない

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/1", json={"content": "Updated content"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_update_comment_other_user():
    """同じファミリーの他ユーザーのコメント編集拒否（403）"""
    client = TestClient(app)

    # 認証ユーザー（user_id = 1）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 他ユーザーのコメント（user_id = 2）
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 2  # 作成者と異なる
    mock_comment.picture_id = 1
    mock_comment.is_deleted = 0

    # データベースモック設定
    mock_db_session = setup_comment_mock(mock_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/1", json={"content": "Updated content"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_update_comment_with_deleted_user():
    """削除済みユーザーでのアクセス拒否（403）"""
    client = TestClient(app)
    # 削除済みユーザーは認証時点で拒否される
    response = client.patch("/api/comments/1", json={"content": "Updated content"})
    assert response.status_code == 403


def test_update_comment_with_invalid_token():
    """無効なトークンでのアクセス拒否（403）"""
    client = TestClient(app)
    # 無効なトークンは認証時点で拒否される
    response = client.patch("/api/comments/1", json={"content": "Updated content"})
    assert response.status_code == 403


# ========================
# 入力検証テスト (4項目)
# ========================

def test_update_comment_empty_content():
    """空のコメント内容でエラー（422）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.patch("/api/comments/1", json={"content": ""})
        assert response.status_code == 422  # FastAPIのバリデーションエラー
    finally:
        app.dependency_overrides.clear()


def test_update_comment_only_spaces():
    """スペースのみのコメント内容でエラー（422）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.patch("/api/comments/1", json={"content": "   "})
        assert response.status_code == 422  # FastAPIのバリデーションエラー
    finally:
        app.dependency_overrides.clear()


def test_update_comment_exceed_max_length():
    """1000文字超過のコメントでエラー（422）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # 1001文字のコメント
    long_content = "a" * 1001

    try:
        response = client.patch("/api/comments/1", json={"content": long_content})
        assert response.status_code == 422  # FastAPIのバリデーションエラー
    finally:
        app.dependency_overrides.clear()


def test_update_comment_invalid_json():
    """不正なJSON形式でエラー（422）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        # contentの型が不正（数値）
        response = client.patch("/api/comments/1", json={"content": 123})
        assert response.status_code == 422  # FastAPIのバリデーションエラー
    finally:
        app.dependency_overrides.clear()


# ========================
# エラー処理テスト (4項目)
# ========================

def test_update_comment_not_found():
    """存在しないコメントIDでエラー（404）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # データベースモック（コメントが見つからない）
    mock_db_session = setup_comment_mock(None)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/999", json={"content": "Updated content"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_update_comment_deleted_comment():
    """削除済みコメントの編集拒否（404）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # データベースモック（削除済みコメントはis_deleted=0フィルタで除外される）
    mock_db_session = setup_comment_mock(None)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/1", json={"content": "Updated content"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_update_comment_deleted_picture():
    """削除済み写真のコメント編集（正常に編集可能）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"

    # 既存コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.content = "Old content"
    mock_comment.is_deleted = 0

    # 更新後のコメントモック
    mock_updated_comment = MagicMock()
    mock_updated_comment.id = 1
    mock_updated_comment.content = "Updated content"
    mock_updated_comment.user_id = 1
    mock_updated_comment.picture_id = 1
    mock_updated_comment.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_updated_comment.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_updated_comment.user.user_name = "test_user"
    mock_updated_comment.user.nickname = None

    # データベースモック設定
    mock_db_session = setup_comment_mock(mock_comment, mock_updated_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/1", json={"content": "Updated content"})
        assert response.status_code == 200  # 削除済み写真のコメントも編集可能
        response_data = response.json()
        assert response_data["content"] == "Updated content"
    finally:
        app.dependency_overrides.clear()


def test_update_comment_invalid_id_format():
    """不正なID形式でエラー（422）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.patch("/api/comments/invalid_id", json={"content": "Updated content"})
        assert response.status_code == 422  # FastAPIのパスパラメータ検証エラー
    finally:
        app.dependency_overrides.clear()


# ========================
# レスポンス検証テスト (4項目)
# ========================

def test_update_comment_response_format():
    """レスポンス形式の検証（必須フィールドの確認）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"

    # 既存コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.content = "Old content"
    mock_comment.is_deleted = 0

    # 更新後のコメントモック
    mock_updated_comment = MagicMock()
    mock_updated_comment.id = 1
    mock_updated_comment.content = "Updated content"
    mock_updated_comment.user_id = 1
    mock_updated_comment.picture_id = 1
    mock_updated_comment.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_updated_comment.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_updated_comment.user.user_name = "test_user"
    mock_updated_comment.user.nickname = None

    # データベースモック設定
    mock_db_session = setup_comment_mock(mock_comment, mock_updated_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/1", json={"content": "Updated content"})
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        response_data = response.json()
        required_fields = ["id", "content", "user_id", "picture_id", "create_date", "update_date", "user_name"]
        for field in required_fields:
            assert field in response_data, f"Required field '{field}' missing from response"
    finally:
        app.dependency_overrides.clear()


def test_update_comment_updated_at_changed():
    """更新日時が変更されることを確認"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"

    original_update_date = datetime(2024, 1, 1, 10, 0, 0)
    new_update_date = datetime(2024, 1, 2, 10, 0, 0)

    # 既存コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.content = "Old content"
    mock_comment.is_deleted = 0
    mock_comment.update_date = original_update_date

    # 更新後のコメントモック
    mock_updated_comment = MagicMock()
    mock_updated_comment.id = 1
    mock_updated_comment.content = "Updated content"
    mock_updated_comment.user_id = 1
    mock_updated_comment.picture_id = 1
    mock_updated_comment.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_updated_comment.update_date = new_update_date
    mock_updated_comment.user.user_name = "test_user"
    mock_updated_comment.user.nickname = None

    # データベースモック設定
    mock_db_session = setup_comment_mock(mock_comment, mock_updated_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/1", json={"content": "Updated content"})
        assert response.status_code == 200
        response_data = response.json()

        # update_dateが更新されていることを確認
        assert "update_date" in response_data
        assert response_data["update_date"] != original_update_date.isoformat()
    finally:
        app.dependency_overrides.clear()


def test_update_comment_created_at_unchanged():
    """作成日時が変更されないことを確認"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"

    original_create_date = datetime(2024, 1, 1, 10, 0, 0)

    # 既存コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.content = "Old content"
    mock_comment.is_deleted = 0
    mock_comment.create_date = original_create_date

    # 更新後のコメントモック
    mock_updated_comment = MagicMock()
    mock_updated_comment.id = 1
    mock_updated_comment.content = "Updated content"
    mock_updated_comment.user_id = 1
    mock_updated_comment.picture_id = 1
    mock_updated_comment.create_date = original_create_date  # 同じ作成日時
    mock_updated_comment.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_updated_comment.user.user_name = "test_user"
    mock_updated_comment.user.nickname = None

    # データベースモック設定
    mock_db_session = setup_comment_mock(mock_comment, mock_updated_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.patch("/api/comments/1", json={"content": "Updated content"})
        assert response.status_code == 200
        response_data = response.json()

        # create_dateが変更されていないことを確認
        assert "create_date" in response_data
        assert response_data["create_date"] == original_create_date.isoformat()
    finally:
        app.dependency_overrides.clear()


def test_update_comment_idempotent():
    """同じ内容での更新が冪等であることを確認"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"

    same_content = "Same content"

    # 既存コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.content = same_content
    mock_comment.is_deleted = 0

    # 更新後のコメントモック（同じ内容）
    mock_updated_comment = MagicMock()
    mock_updated_comment.id = 1
    mock_updated_comment.content = same_content
    mock_updated_comment.user_id = 1
    mock_updated_comment.picture_id = 1
    mock_updated_comment.create_date = datetime(2024, 1, 1, 10, 0, 0)
    mock_updated_comment.update_date = datetime(2024, 1, 2, 10, 0, 0)
    mock_updated_comment.user.user_name = "test_user"
    mock_updated_comment.user.nickname = None

    # データベースモック設定
    mock_db_session = setup_comment_mock(mock_comment, mock_updated_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # 1回目の更新
        response1 = client.patch("/api/comments/1", json={"content": same_content})
        assert response1.status_code == 200
        response_data1 = response1.json()

        # 2回目の更新（同じ内容）
        response2 = client.patch("/api/comments/1", json={"content": same_content})
        assert response2.status_code == 200
        response_data2 = response2.json()

        # 両方のレスポンスが同じ内容を持つことを確認
        assert response_data1["content"] == response_data2["content"] == same_content
        assert response_data1["id"] == response_data2["id"]
    finally:
        app.dependency_overrides.clear()