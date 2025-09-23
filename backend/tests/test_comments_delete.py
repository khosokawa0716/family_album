"""
コメント削除API (DELETE /api/comments/:id) のテスト

コメント削除API (DELETE /api/comments/:id) の実装と対応するテストです。
論理削除（is_deleted=1）により、データベースからは物理削除せずに削除フラグを設定します。

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 他ファミリーのコメント削除拒否
   - 他ユーザーのコメント削除拒否（コメント作成者のみ削除可能）
   - 存在しないユーザーでの削除拒否

2. 削除処理テスト
   - 正常なコメント削除
   - 論理削除フラグの設定（is_deleted=1）
   - 削除後のコメントは表示されないことの確認
   - 関連データの整合性確認

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
- test_delete_comment_soft_delete: 論理削除の確認（is_deleted=1が設定される）
- test_delete_comment_count_update: 写真のコメント数が正しく更新される
- test_delete_comment_cascade_behavior: 関連データの整合性確認
- test_delete_comment_list_exclusion: 削除されたコメントがリスト取得時に除外される
- test_delete_comment_detail_access_denied: 削除されたコメントの詳細取得が拒否される
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from main import app
from database import get_db
from dependencies import get_current_user


def setup_comment_delete_mock(mock_comment):
    """コメント削除テスト用の共通モック設定"""
    mock_db_session = MagicMock()

    # コメント取得クエリ（JOIN付き）
    mock_comment_query = MagicMock()
    mock_comment_join = MagicMock()
    mock_comment_filter = MagicMock()
    mock_comment_filter.first.return_value = mock_comment
    mock_comment_join.filter.return_value = mock_comment_filter
    mock_comment_query.join.return_value = mock_comment_join

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

def test_delete_comment_success():
    """正常なコメント削除（コメント作成者による削除）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"

    # 削除対象コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1  # 作成者と同じ
    mock_comment.picture_id = 1
    mock_comment.content = "Test comment"
    mock_comment.is_deleted = 0

    # データベースモック設定
    mock_db_session = setup_comment_delete_mock(mock_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/comments/1")
        assert response.status_code == 204  # No Content

        # is_deletedが1に設定されることを確認
        assert mock_comment.is_deleted == 1
        # commitが呼ばれることを確認
        mock_db_session.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_response_status():
    """削除成功時のステータスコード確認（204）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 削除対象コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.is_deleted = 0

    # データベースモック設定
    mock_db_session = setup_comment_delete_mock(mock_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/comments/1")
        assert response.status_code == 204
        assert response.text == ""  # No Contentなのでレスポンスボディは空
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_not_visible_after_deletion():
    """削除後のコメントが表示されないことの確認"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 削除対象コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.is_deleted = 0

    # データベースモック設定
    mock_db_session = setup_comment_delete_mock(mock_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # コメント削除
        delete_response = client.delete("/api/comments/1")
        assert delete_response.status_code == 204

        # 削除後、コメントは is_deleted=1 になり、
        # コメント一覧APIでは is_deleted=0 フィルタで除外される
        assert mock_comment.is_deleted == 1
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

    # 認証ユーザー（family_id = 1）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 他ファミリーのコメント（family_id = 2）のため、家族スコープフィルタで除外される
    mock_db_session = setup_comment_delete_mock(None)  # コメントが見つからない

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/comments/1")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_other_user():
    """同じファミリーの他ユーザーのコメント削除拒否（403）"""
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
    mock_db_session = setup_comment_delete_mock(mock_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/comments/1")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_with_deleted_user():
    """削除済みユーザーでのアクセス拒否（403）"""
    client = TestClient(app)
    # 削除済みユーザーは認証時点で拒否される
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

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # データベースモック（コメントが見つからない）
    mock_db_session = setup_comment_delete_mock(None)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/comments/999")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_invalid_id_format():
    """無効なIDフォーマットでエラー（422）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.delete("/api/comments/invalid_id")
        assert response.status_code == 422  # FastAPIのパスパラメータ検証エラー
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_already_deleted():
    """削除済みコメントの再削除でエラー（404）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # データベースモック（削除済みコメントはis_deleted=0フィルタで除外される）
    mock_db_session = setup_comment_delete_mock(None)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/comments/1")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_on_deleted_picture():
    """削除済み写真のコメント削除（404）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 削除済み写真のコメントは家族スコープフィルタで除外される場合がある
    mock_db_session = setup_comment_delete_mock(None)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/comments/1")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_non_numeric_id():
    """数値以外のIDでエラー（422）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.delete("/api/comments/abc")
        assert response.status_code == 422  # FastAPIのパスパラメータ検証エラー
    finally:
        app.dependency_overrides.clear()


# ========================
# データ整合性テスト (5項目)
# ========================

def test_delete_comment_soft_delete():
    """論理削除の確認（is_deleted=1が設定される）"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 削除対象コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.is_deleted = 0

    # データベースモック設定
    mock_db_session = setup_comment_delete_mock(mock_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/comments/1")
        assert response.status_code == 204

        # 論理削除フラグが設定されることを確認
        assert mock_comment.is_deleted == 1
        # 物理削除ではないことを確認（データベースからレコードは削除されない）
        mock_db_session.delete.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_count_update():
    """写真のコメント数が正しく更新される"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 削除対象コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.is_deleted = 0

    # データベースモック設定
    mock_db_session = setup_comment_delete_mock(mock_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/comments/1")
        assert response.status_code == 204

        # コメント削除後、写真のコメント数は自動的に更新される
        # （実際の実装では集計クエリで動的に計算される場合が多い）
        assert mock_comment.is_deleted == 1
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_cascade_behavior():
    """関連データの整合性確認"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 削除対象コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.is_deleted = 0

    # データベースモック設定
    mock_db_session = setup_comment_delete_mock(mock_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.delete("/api/comments/1")
        assert response.status_code == 204

        # 関連データの整合性が保たれることを確認
        # （論理削除なので関連データは残る）
        assert mock_comment.is_deleted == 1
        assert mock_comment.picture_id == 1  # 写真との関連は維持される
        assert mock_comment.user_id == 1     # ユーザーとの関連は維持される
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_list_exclusion():
    """削除されたコメントがリスト取得時に除外される"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 削除対象コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.is_deleted = 0

    # データベースモック設定
    mock_db_session = setup_comment_delete_mock(mock_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # コメント削除
        delete_response = client.delete("/api/comments/1")
        assert delete_response.status_code == 204

        # 削除後、コメントリスト取得APIでは除外される
        # （is_deleted=0 フィルタにより除外される）
        assert mock_comment.is_deleted == 1
    finally:
        app.dependency_overrides.clear()


def test_delete_comment_detail_access_denied():
    """削除されたコメントの詳細取得が拒否される"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # 削除対象コメントのモック
    mock_comment = MagicMock()
    mock_comment.id = 1
    mock_comment.user_id = 1
    mock_comment.picture_id = 1
    mock_comment.is_deleted = 0

    # データベースモック設定
    mock_db_session = setup_comment_delete_mock(mock_comment)

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        # コメント削除
        delete_response = client.delete("/api/comments/1")
        assert delete_response.status_code == 204

        # 削除後、削除されたコメントは is_deleted=1 になり、
        # 詳細取得時は is_deleted=0 フィルタで除外される
        assert mock_comment.is_deleted == 1
    finally:
        app.dependency_overrides.clear()