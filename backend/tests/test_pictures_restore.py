"""
PATCH /api/pictures/:id/restore APIのテストファイル（写真復元）

写真復元API仕様:
- 認証済みユーザーが自分の家族の削除済み写真を復元
- 復元後はstatusを1に変更し、deleted_atをNULLに設定
- 家族スコープでのアクセス制御
- 既に有効な写真は復元不可

テスト観点:
1. 認証・認可テスト
   - 未認証ユーザーのアクセス拒否
   - 他ファミリーの写真への復元拒否
   - 存在しないユーザーでの復元拒否

2. アクセス制御テスト
   - 自分の家族の削除済み写真の復元成功
   - 他の家族の写真復元試行の拒否（404）
   - 存在しない写真IDでの404エラー

3. 復元状態テスト
   - 削除済み写真（status=0）の復元成功
   - 既に有効な写真（status=1）の復元試行（404）
   - 復元後のステータス・タイムスタンプ確認

4. データベース操作テスト
   - statusが1に更新される
   - deleted_atがNULLにクリアされる
   - updated_atが現在時刻に更新される
   - 他のフィールドは変更されない

5. レスポンステスト
   - 復元成功時の200ステータス
   - エラー時の適切なエラーレスポンス
   - レスポンス形式の確認

テスト項目一覧: 18項目
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from main import app
from models import User, Picture
from database import get_db
from dependencies import get_current_user


class TestPicturesRestore:
    """PATCH /api/pictures/:id/restore APIのテストクラス"""

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

        # 削除済み写真（復元対象）
        self.deleted_picture = MagicMock(spec=Picture)
        self.deleted_picture.id = 1
        self.deleted_picture.family_id = self.test_user.family_id
        self.deleted_picture.title = "Deleted Picture"
        self.deleted_picture.status = 0  # 削除済み
        self.deleted_picture.uploaded_by = self.test_user.id
        self.deleted_picture.create_date = datetime.now(timezone.utc)
        self.deleted_picture.update_date = datetime.now(timezone.utc)
        self.deleted_picture.deleted_at = datetime.now(timezone.utc)

        # 有効な写真（復元不可）
        self.active_picture = MagicMock(spec=Picture)
        self.active_picture.id = 2
        self.active_picture.family_id = self.test_user.family_id
        self.active_picture.title = "Active Picture"
        self.active_picture.status = 1  # 有効
        self.active_picture.uploaded_by = self.test_user.id
        self.active_picture.create_date = datetime.now(timezone.utc)
        self.active_picture.update_date = datetime.now(timezone.utc)
        self.active_picture.deleted_at = None

        # 他の家族の削除済み写真
        self.other_family_picture = MagicMock(spec=Picture)
        self.other_family_picture.id = 3
        self.other_family_picture.family_id = 999  # 異なる家族ID
        self.other_family_picture.title = "Other Family Picture"
        self.other_family_picture.status = 0
        self.other_family_picture.uploaded_by = 999
        self.other_family_picture.create_date = datetime.now(timezone.utc)
        self.other_family_picture.update_date = datetime.now(timezone.utc)
        self.other_family_picture.deleted_at = datetime.now(timezone.utc)

    def teardown_method(self):
        """各テストメソッド実行後のクリーンアップ"""
        app.dependency_overrides.clear()

    # ========================================
    # 1. 成功パターン（2項目）
    # ========================================

    def test_restore_deleted_picture_success(self):
        """正常復元: 削除済み写真の正常復元"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Picture restored successfully"

        # 復元処理が実行されたことを確認
        assert self.deleted_picture.status == 1
        assert self.deleted_picture.deleted_at is None
        assert self.deleted_picture.update_date is not None
        mock_db.commit.assert_called_once()

    def test_restore_response_format(self):
        """レスポンス確認: 復元成功時の適切なレスポンス"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()
        assert isinstance(response.json()["message"], str)

    # ========================================
    # 2. 認証・認可（4項目）
    # ========================================

    def test_restore_without_auth(self):
        """未認証拒否: 認証なしでのアクセス拒否"""
        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_restore_other_family_picture(self):
        """他ファミリー拒否: 他ファミリーの写真への復元拒否"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.patch(f"{self.base_url}/{self.other_family_picture.id}/restore")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Picture not found or already restored"

    def test_restore_with_invalid_user(self):
        """存在しないユーザー: 無効なユーザーでの復元拒否"""
        invalid_user = MagicMock(spec=User)
        invalid_user.id = 999
        invalid_user.family_id = 999
        invalid_user.status = 0

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: invalid_user

        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_family_scope_access_control(self):
        """権限確認: 同一ファミリー内でのアクセス権確認"""
        # 同一ファミリーの別ユーザー
        family_user = MagicMock(spec=User)
        family_user.id = 2
        family_user.family_id = self.test_user.family_id  # 同じファミリー
        family_user.status = 1

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: family_user

        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")

        assert response.status_code == status.HTTP_200_OK

    # ========================================
    # 3. データ状態・ビジネスロジック（6項目）
    # ========================================

    def test_restore_nonexistent_picture(self):
        """存在しない写真ID: 無効な写真IDでの復元試行"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.patch(f"{self.base_url}/999/restore")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Picture not found or already restored"

    def test_restore_active_picture(self):
        """有効写真の復元: 既に有効な写真への復元試行"""
        mock_db = Mock()
        # 有効な写真はstatus=0フィルターで除外されるためNoneが返される
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.patch(f"{self.base_url}/{self.active_picture.id}/restore")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Picture not found or already restored"

    def test_status_change_confirmation(self):
        """ステータス変更確認: status=0→1への変更確認"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        assert self.deleted_picture.status == 0  # 復元前

        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")

        assert response.status_code == status.HTTP_200_OK
        assert self.deleted_picture.status == 1  # 復元後

    def test_deleted_at_clear_confirmation(self):
        """削除日時クリア: deleted_atのNULLクリア確認"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        assert self.deleted_picture.deleted_at is not None  # 復元前

        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")

        assert response.status_code == status.HTTP_200_OK
        assert self.deleted_picture.deleted_at is None  # 復元後

    def test_updated_at_refresh(self):
        """変更日時更新: updated_atの更新確認"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        original_updated_at = self.deleted_picture.update_date

        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")

        assert response.status_code == status.HTTP_200_OK
        assert self.deleted_picture.update_date != original_updated_at

    def test_other_fields_preservation(self):
        """他フィールド保持: 他の写真データの保持確認"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        # 復元前の値を保存
        original_title = self.deleted_picture.title
        original_family_id = self.deleted_picture.family_id
        original_uploaded_by = self.deleted_picture.uploaded_by
        original_created_at = self.deleted_picture.create_date

        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")

        assert response.status_code == status.HTTP_200_OK

        # 他のフィールドが変更されていないことを確認
        assert self.deleted_picture.title == original_title
        assert self.deleted_picture.family_id == original_family_id
        assert self.deleted_picture.uploaded_by == original_uploaded_by
        assert self.deleted_picture.create_date == original_created_at

    # ========================================
    # 4. エラーハンドリング（4項目）
    # ========================================

    def test_database_connection_error(self):
        """DB接続エラー: データベース接続エラー時の処理"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.side_effect = Exception("Database connection error")
        mock_db.rollback.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to restore picture"

    def test_transaction_rollback(self):
        """トランザクションエラー: 更新処理失敗時のロールバック"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.side_effect = Exception("Transaction error")
        mock_db.rollback.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to restore picture"
        mock_db.rollback.assert_called_once()

    def test_invalid_id_format(self):
        """無効ID形式: 文字列など無効なID形式の処理"""
        mock_db = Mock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        invalid_ids = ["not-a-number", "abc"]

        for invalid_id in invalid_ids:
            response = self.client.patch(f"{self.base_url}/{invalid_id}/restore")
            # FastAPIのパス変換エラー、または404
            assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_404_NOT_FOUND]

    def test_sql_injection_protection(self):
        """SQLインジェクション: セキュリティ攻撃への耐性"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        malicious_ids = ["1; DROP TABLE pictures;", "1' OR '1'='1", "1 UNION SELECT * FROM users"]

        for malicious_id in malicious_ids:
            response = self.client.patch(f"{self.base_url}/{malicious_id}/restore")
            # 数値以外はパス変換でエラーになる
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ========================================
    # 5. HTTP仕様（2項目）
    # ========================================

    def test_patch_method_implementation(self):
        """HTTPメソッド: PATCHメソッドの正確な実装"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.return_value = None

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        # PATCHメソッドが正しく実装されていることを確認
        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")
        assert response.status_code == status.HTTP_200_OK

        # 他のメソッドは許可されない
        get_response = self.client.get(f"{self.base_url}/{self.deleted_picture.id}/restore")
        assert get_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        post_response = self.client.post(f"{self.base_url}/{self.deleted_picture.id}/restore")
        assert post_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_status_codes(self):
        """ステータスコード: 各ケースでの適切なHTTPステータス返却"""
        mock_db = Mock()

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        # 成功: 200
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.return_value = None
        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")
        assert response.status_code == status.HTTP_200_OK

        # 写真が見つからない: 404
        mock_db.query.return_value.filter.return_value.first.return_value = None
        response = self.client.patch(f"{self.base_url}/999/restore")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # データベースエラー: 500
        mock_db.query.return_value.filter.return_value.first.return_value = self.deleted_picture
        mock_db.commit.side_effect = Exception("DB Error")
        response = self.client.patch(f"{self.base_url}/{self.deleted_picture.id}/restore")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR