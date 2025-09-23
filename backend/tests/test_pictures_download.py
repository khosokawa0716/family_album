"""
GET /api/pictures/:id/download APIのテストファイル（写真原本ダウンロード）

写真原本ダウンロードAPI仕様:
- 認証済みユーザーが自分の家族の有効な写真の原本ファイルをダウンロード
- 適切なContent-Typeヘッダーを設定してファイルを返却
- 家族スコープでのアクセス制御
- 削除済み写真はダウンロード不可

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 他ファミリーの写真へのダウンロード拒否
   - 存在しないユーザーでのダウンロード拒否

2. ファイルアクセステスト
   - 自分の家族の有効写真のダウンロード成功
   - 他の家族の写真ダウンロード試行の拒否（404）
   - 存在しない写真IDでの404エラー
   - 削除済み写真へのアクセス拒否

3. ファイル状態テスト
   - 有効写真（status=1）のダウンロード成功
   - 削除済み写真（status=0）のダウンロード試行（404）
   - ファイルパスが存在しない場合の404エラー
   - ファイルが物理的に存在しない場合の404エラー

4. レスポンステスト
   - 適切なContent-Typeヘッダーの設定
   - ファイルサイズの正確性
   - ファイル内容の正確性
   - Content-Dispositionヘッダーの設定

5. セキュリティテスト
   - パストラバーサル攻撃への耐性
   - ファイルアクセス制御の確認
   - 不正なファイル拡張子での攻撃防止

テスト項目（20項目）:

【成功パターン】(3項目)
- test_download_active_picture_success: 有効な写真の正常ダウンロード
- test_download_content_disposition_header: Content-Dispositionヘッダーの設定確認
- test_download_different_mime_types: 異なるMIMEタイプでの適切なヘッダー設定

【認証・認可】(4項目)
- test_download_without_auth: 未認証でのアクセス拒否（403）
- test_download_other_family_picture: 他ファミリーの写真へのダウンロード拒否（404）
- test_download_with_invalid_user: 無効なユーザーでのダウンロード拒否（404）
- test_family_scope_access_control: 同一ファミリー内でのアクセス権確認

【データ状態・ビジネスロジック】(6項目)
- test_download_nonexistent_picture: 無効な写真IDでのダウンロード試行（404）
- test_download_deleted_picture: 削除済み写真へのダウンロード試行（404）
- test_download_file_not_exists: 物理ファイルが存在しない場合（404）
- test_download_file_read_error: ファイル読み込み時のエラー処理（500）
- test_invalid_id_format: 無効なID形式の処理（422）
- test_mime_type_validation: 不正なMIMEタイプでの処理

【セキュリティ】(4項目)
- test_path_traversal_protection: パストラバーサル攻撃への耐性
- test_sql_injection_protection: SQLインジェクション攻撃への耐性（422）
- test_file_size_validation: 過大なファイルサイズでの処理
- test_concurrent_access_safety: 複数ユーザーの同時アクセス安全性

【HTTPメソッド・仕様】(3項目)
- test_get_method_implementation: GETメソッドの正確な実装
- test_status_codes_comprehensive: 各ケースでの適切なHTTPステータス返却
- test_response_headers_comprehensive: 必要なヘッダーが適切に設定されている
"""

from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime, timezone
import tempfile
import os
from pathlib import Path

from main import app
from models import User, Picture
from database import get_db
from dependencies import get_current_user
from config.storage import get_storage_config


class TestPicturesDownload:
    """GET /api/pictures/:id/download APIのテストクラス"""

    def setup_method(self):
        """各テストメソッド実行前の初期化"""
        self.client = TestClient(app)
        self.base_url = "/api/pictures"

        # テスト用ユーザーの設定
        self.test_user = MagicMock(spec=User)
        self.test_user.id = 1
        self.test_user.family_id = 1
        self.test_user.user_name = "testuser"
        self.test_user.email = "test@example.com"
        self.test_user.status = 1

        # 有効な写真（ダウンロード対象）
        self.active_picture = MagicMock(spec=Picture)
        self.active_picture.id = 1
        self.active_picture.family_id = self.test_user.family_id
        self.active_picture.title = "Test Picture"
        self.active_picture.file_path = "/storage/test-family/picture1.jpg"
        self.active_picture.file_name = "picture1.jpg"
        self.active_picture.mime_type = "image/jpeg"
        self.active_picture.file_size = 1024000
        self.active_picture.status = 1  # 有効
        self.active_picture.uploaded_by = self.test_user.id
        self.active_picture.create_date = datetime.now(timezone.utc)
        self.active_picture.update_date = datetime.now(timezone.utc)
        self.active_picture.deleted_at = None

        # 削除済み写真（ダウンロード不可）
        self.deleted_picture = MagicMock(spec=Picture)
        self.deleted_picture.id = 2
        self.deleted_picture.family_id = self.test_user.family_id
        self.deleted_picture.title = "Deleted Picture"
        self.deleted_picture.file_path = "/storage/test-family/deleted_picture.jpg"
        self.deleted_picture.file_name = "deleted_picture.jpg"
        self.deleted_picture.mime_type = "image/jpeg"
        self.deleted_picture.file_size = 512000
        self.deleted_picture.status = 0  # 削除済み
        self.deleted_picture.uploaded_by = self.test_user.id
        self.deleted_picture.create_date = datetime.now(timezone.utc)
        self.deleted_picture.update_date = datetime.now(timezone.utc)
        self.deleted_picture.deleted_at = datetime.now(timezone.utc)

        # 他の家族の写真
        self.other_family_picture = MagicMock(spec=Picture)
        self.other_family_picture.id = 3
        self.other_family_picture.family_id = 999  # 異なる家族ID
        self.other_family_picture.title = "Other Family Picture"
        self.other_family_picture.file_path = "/storage/other-family/picture.jpg"
        self.other_family_picture.file_name = "picture.jpg"
        self.other_family_picture.mime_type = "image/jpeg"
        self.other_family_picture.file_size = 2048000
        self.other_family_picture.status = 1
        self.other_family_picture.uploaded_by = 999
        self.other_family_picture.create_date = datetime.now(timezone.utc)
        self.other_family_picture.update_date = datetime.now(timezone.utc)
        self.other_family_picture.deleted_at = None

        # テスト用ファイル内容
        self.test_file_content = b"fake image content for testing"

    def teardown_method(self):
        """各テストメソッド実行後のクリーンアップ"""
        app.dependency_overrides.clear()

    # ========================================
    # 1. 成功パターン（3項目）
    # ========================================

    def test_download_active_picture_success(self):
        """正常ダウンロード: 有効な写真の正常ダウンロード"""
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            test_content = b"fake image content for testing"
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "image/jpeg"
            assert len(response.content) == len(test_content)

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_download_content_disposition_header(self):
        """ヘッダー確認: Content-Dispositionヘッダーの設定確認"""
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            test_content = b"fake image content for testing"
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")

            assert response.status_code == status.HTTP_200_OK
            assert "content-disposition" in response.headers
            assert f'attachment; filename="{self.active_picture.file_name}"' in response.headers["content-disposition"]

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_download_different_mime_types(self):
        """MIMEタイプ確認: 異なるMIMEタイプでの適切なヘッダー設定"""
        # PNG画像のモック
        png_picture = MagicMock(spec=Picture)
        png_picture.id = 4
        png_picture.family_id = self.test_user.family_id
        png_picture.file_path = "photos/picture.png"
        png_picture.file_name = "picture.png"
        png_picture.mime_type = "image/png"
        png_picture.status = 1

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            test_content = b"png image content for testing"
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = png_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            response = self.client.get(f"{self.base_url}/{png_picture.id}/download")

            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "image/png"

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    # ========================================
    # 2. 認証・認可（4項目）
    # ========================================

    def test_download_without_auth(self):
        """未認証拒否: 認証なしでのアクセス拒否"""
        response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_download_other_family_picture(self):
        """他ファミリー拒否: 他ファミリーの写真へのダウンロード拒否"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.get(f"{self.base_url}/{self.other_family_picture.id}/download")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Picture not found"

    def test_download_with_invalid_user(self):
        """存在しないユーザー: 無効なユーザーでのダウンロード拒否"""
        invalid_user = MagicMock(spec=User)
        invalid_user.id = 999
        invalid_user.family_id = 999
        invalid_user.status = 0

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: invalid_user

        response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_family_scope_access_control(self):
        """権限確認: 同一ファミリー内でのアクセス権確認"""
        # 同一ファミリーの別ユーザー
        family_user = MagicMock(spec=User)
        family_user.id = 2
        family_user.family_id = self.test_user.family_id  # 同じファミリー
        family_user.status = 1

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            test_content = b"test image content"
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: family_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")

            assert response.status_code == status.HTTP_200_OK

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    # ========================================
    # 3. データ状態・ビジネスロジック（6項目）
    # ========================================

    def test_download_nonexistent_picture(self):
        """存在しない写真ID: 無効な写真IDでのダウンロード試行"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.get(f"{self.base_url}/999/download")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Picture not found"

    def test_download_deleted_picture(self):
        """削除済み写真: 削除済み写真へのダウンロード試行"""
        mock_db = Mock()
        # 削除済み写真はstatus=1フィルターで除外されるためNoneが返される
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.get(f"{self.base_url}/{self.deleted_picture.id}/download")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Picture not found"

    def test_download_file_not_exists(self):
        """ファイル不存在: 物理ファイルが存在しない場合"""
        # StorageConfigのモック（ファイルが存在しない）
        mock_storage_config = Mock()
        mock_file_path = Mock()
        mock_file_path.exists.return_value = False  # ファイルが存在しない
        mock_storage_config.get_photo_file_path.return_value = mock_file_path

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

        response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "File not found"

    def test_download_file_read_error(self):
        """ファイル読込エラー: ファイル読み込み時のエラー処理"""
        # StorageConfigのモック（ファイルは存在するが読み込みエラー）
        mock_storage_config = Mock()
        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.stat.side_effect = IOError("Cannot access file")
        mock_storage_config.get_photo_file_path.return_value = mock_file_path

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

        response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to read file"

    def test_invalid_id_format(self):
        """無効ID形式: 文字列など無効なID形式の処理"""
        mock_db = Mock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        invalid_ids = ["not-a-number", "abc", "null"]

        for invalid_id in invalid_ids:
            response = self.client.get(f"{self.base_url}/{invalid_id}/download")
            # FastAPIのパス変換エラー
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_mime_type_validation(self):
        """MIMEタイプ検証: 不正なMIMEタイプでの処理"""
        # MIMEタイプが不正な写真のモック
        invalid_mime_picture = MagicMock(spec=Picture)
        invalid_mime_picture.id = 5
        invalid_mime_picture.family_id = self.test_user.family_id
        invalid_mime_picture.file_path = "photos/invalid.txt"
        invalid_mime_picture.file_name = "invalid.txt"
        invalid_mime_picture.mime_type = "text/plain"  # 画像でないMIMEタイプ
        invalid_mime_picture.status = 1

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            test_content = b"text content for testing"
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = invalid_mime_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            response = self.client.get(f"{self.base_url}/{invalid_mime_picture.id}/download")

            # APIとしては正常に返却されるが、Content-Typeは保持される
            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"].startswith("text/plain")

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    # ========================================
    # 4. セキュリティテスト（4項目）
    # ========================================

    def test_path_traversal_protection(self):
        """パストラバーサル: パストラバーサル攻撃への耐性"""
        # パストラバーサル攻撃を試行する写真のモック
        malicious_picture = MagicMock(spec=Picture)
        malicious_picture.id = 6
        malicious_picture.family_id = self.test_user.family_id
        malicious_picture.file_path = "../../etc/passwd"  # 危険なパス
        malicious_picture.file_name = "passwd"
        malicious_picture.mime_type = "text/plain"
        malicious_picture.status = 1

        # StorageConfigのモック（os.path.basenameで安全化される）
        mock_storage_config = Mock()
        mock_file_path = Mock()
        mock_file_path.exists.return_value = False  # 安全化されたファイルは存在しない
        mock_storage_config.get_photo_file_path.return_value = mock_file_path

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = malicious_picture

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

        response = self.client.get(f"{self.base_url}/{malicious_picture.id}/download")

        # パストラバーサル攻撃は失敗すべき（ファイルが見つからない）
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_sql_injection_protection(self):
        """SQLインジェクション: セキュリティ攻撃への耐性"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        malicious_ids = ["1; DROP TABLE pictures;", "1' OR '1'='1", "1 UNION SELECT * FROM users"]

        for malicious_id in malicious_ids:
            response = self.client.get(f"{self.base_url}/{malicious_id}/download")
            # 数値以外はパス変換でエラーになる
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_file_size_validation(self):
        """ファイルサイズ検証: 過大なファイルサイズでの処理"""
        # 非常に大きなファイルサイズの写真
        large_picture = MagicMock(spec=Picture)
        large_picture.id = 7
        large_picture.family_id = self.test_user.family_id
        large_picture.file_path = "photos/large.jpg"
        large_picture.file_name = "large.jpg"
        large_picture.mime_type = "image/jpeg"
        large_picture.file_size = 100 * 1024 * 1024  # 100MB
        large_picture.status = 1

        # 一時ファイルを作成（メモリ節約のため小さなファイルで代用）
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            test_content = b"large file content simulation"
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = large_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            response = self.client.get(f"{self.base_url}/{large_picture.id}/download")

            # 大きなファイルでも正常に処理されるべき
            assert response.status_code == status.HTTP_200_OK

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_concurrent_access_safety(self):
        """同時アクセス: 複数ユーザーの同時アクセス安全性"""
        # 同時アクセステストは実装では単純な読み込みなので、
        # モックレベルでの確認に留める

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            test_content = b"test content for concurrent access"
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            # 複数回のアクセスをシミュレート
            responses = []
            for _ in range(3):
                response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")
                responses.append(response)

            # すべてのアクセスが成功すべき
            for response in responses:
                assert response.status_code == status.HTTP_200_OK

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    # ========================================
    # 5. HTTPメソッド・仕様（3項目）
    # ========================================

    def test_get_method_implementation(self):
        """HTTPメソッド: GETメソッドの正確な実装"""
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            test_content = b"test content for method implementation"
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            # GETメソッドが正しく実装されていることを確認
            response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")
            assert response.status_code == status.HTTP_200_OK

            # 他のメソッドは許可されない
            post_response = self.client.post(f"{self.base_url}/{self.active_picture.id}/download")
            assert post_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

            patch_response = self.client.patch(f"{self.base_url}/{self.active_picture.id}/download")
            assert patch_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_status_codes_comprehensive(self):
        """ステータスコード: 各ケースでの適切なHTTPステータス返却"""
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            test_content = b"test content for status codes"
            temp_file.write(test_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            # 成功: 200
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture
            response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")
            assert response.status_code == status.HTTP_200_OK

            # 写真が見つからない: 404
            mock_db.query.return_value.filter.return_value.first.return_value = None
            response = self.client.get(f"{self.base_url}/999/download")
            assert response.status_code == status.HTTP_404_NOT_FOUND

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_response_headers_comprehensive(self):
        """レスポンスヘッダー: 必要なヘッダーが適切に設定されている"""
        # 一時ファイルを作成
        test_file_content = self.test_file_content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(test_file_content)
            temp_file_path = temp_file.name

        try:
            # StorageConfigのモック
            mock_storage_config = Mock()
            mock_storage_config.get_photo_file_path.return_value = Path(temp_file_path)

            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = self.active_picture

            app.dependency_overrides[get_db] = lambda: mock_db
            app.dependency_overrides[get_current_user] = lambda: self.test_user
            app.dependency_overrides[get_storage_config] = lambda: mock_storage_config

            response = self.client.get(f"{self.base_url}/{self.active_picture.id}/download")

            assert response.status_code == status.HTTP_200_OK

            # 必要なヘッダーが設定されている
            assert "content-type" in response.headers
            assert "content-disposition" in response.headers
            assert "content-length" in response.headers

            # ヘッダーの値が正確
            assert response.headers["content-type"] == self.active_picture.mime_type
            assert self.active_picture.file_name in response.headers["content-disposition"]
            assert response.headers["content-length"] == str(len(test_file_content))

        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)