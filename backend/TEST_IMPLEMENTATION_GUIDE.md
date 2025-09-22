# テスト実装ガイドライン

このドキュメントは、`backend/tests/` ディレクトリの既存テストコードを分析して作成された、テスト実装時の標準化されたガイドラインです。

## 📂 プロジェクト構造

```
backend/tests/
├── conftest.py                 # pytest設定・共通フィクスチャ
├── test_auth.py               # JWT認証・認可機能のテスト
├── test_health.py             # ヘルスチェックAPI
├── test_login.py              # ログインAPI
├── test_logout.py             # ログアウトAPI
├── test_pictures_*.py         # 写真関連API群
├── test_users_*.py            # ユーザー関連API群
└── [各APIエンドポイント毎のテストファイル]
```

## 🎯 テストファイルの命名規則

- **パターン**: `test_{機能名}_{操作名}.py`
- **例**:
  - `test_pictures_upload.py` (写真アップロード)
  - `test_users_edit.py` (ユーザー編集)
  - `test_auth.py` (認証全般)

## 📋 テストファイルの基本構造

### 1. ファイルヘッダー（必須）

```python
"""
{API仕様の説明}

{API仕様詳細}
- 認証要件
- 機能概要
- 重要な制約事項

テスト観点:
1. 認証・認可テスト
   - 具体的な観点

2. {機能固有の観点}
   - 具体的な観点

テスト項目:
- test_function_name: 説明
"""
```

### 2. インポート文

```python
from unittest.mock import MagicMock, Mock, patch
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
# その他必要なインポート
```

### 3. テスト関数の命名

```python
def test_{機能}_{状況}_{期待結果}(client, monkeypatch):
    """テストの説明"""
    # テスト実装
```

## 🔧 共通テストパターン

### 1. 基本的なモック設定パターン（推奨）

```python
def test_example():
    """推奨：app.dependency_overridesを使用した方法"""
    client = TestClient(app)

    # 認証ユーザーのモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1
    mock_user.user_name = "test_user"

    # データベースモック
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user
    mock_db_session.query.return_value = mock_query

    # dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/endpoint")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
```

### 2. 従来のモック設定パターン（非推奨）

```python
def test_example_legacy(client, monkeypatch):
    """従来方法：monkeypatchを使用（非推奨）"""
    # データベースモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.user_name = "test_user"

    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_user

    mock_db_session = MagicMock()
    mock_db_session.query.return_value = mock_query

    from database import db
    monkeypatch.setattr(db, "session", mock_db_session)
    monkeypatch.setattr("dependencies.get_current_user", lambda: mock_user)
```

### 3. 複雑なクエリチェーンのモック

```python
def setup_mock_query_chain():
    """JOIN、filter、order_byなどのチェーンクエリのモック"""
    mock_query = MagicMock()
    mock_join_query = MagicMock()
    mock_filter_query = MagicMock()
    mock_order_query = MagicMock()

    mock_query.join.return_value = mock_join_query
    mock_join_query.filter.return_value = mock_filter_query
    mock_filter_query.order_by.return_value = mock_order_query

    return mock_query, mock_order_query

def test_complex_query():
    """複雑なクエリチェーンのテスト例"""
    # コメントクエリ例：query(Comment).join(User).filter(...).order_by(...).all()
    mock_comment_query, mock_order_query = setup_mock_query_chain()
    mock_order_query.all.return_value = [mock_comment1, mock_comment2]

    def query_side_effect(model):
        if model.__name__ == 'Comment':
            return mock_comment_query
        return MagicMock()

    mock_db_session.query.side_effect = query_side_effect
```

### 4. ファイル操作モックパターン

```python
def test_file_operation():
    """ファイル操作のモック例"""
    client = TestClient(app)

    # ファイル存在チェック
    with patch("os.path.exists", return_value=True):
        # ファイル読み込み
        mock_file_content = b"test image data"
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            # dependency overrides
            app.dependency_overrides[get_current_user] = lambda: mock_user

            try:
                response = client.get("/api/file/download")
                assert response.status_code == 200
            finally:
                app.dependency_overrides.clear()
```

## ✅ 必須テストケースパターン

### 1. 認証・認可テスト（全API共通）

```python
def test_unauthorized_access():
    """未認証アクセスの拒否"""
    client = TestClient(app)
    response = client.get("/api/endpoint")
    assert response.status_code == 403  # FastAPIのデフォルト挙動

def test_other_family_access_denied():
    """他家族データへのアクセス拒否"""
    client = TestClient(app)

    # 認証ユーザー（family_id = 1）
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # データベースモック（他家族のデータは家族スコープで除外される）
    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None  # 除外される

    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/endpoint/1")
        assert response.status_code == 404  # 見つからないとして処理
    finally:
        app.dependency_overrides.clear()
```

### 2. 正常系テスト

```python
def test_success_case():
    """正常なリクエストの成功"""
    client = TestClient(app)

    # 認証ユーザーモック
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    # データベースモック
    mock_result = MagicMock()
    mock_result.id = 1
    mock_result.name = "test_data"

    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_result
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.post("/api/endpoint", json={"name": "test_data"})
        assert response.status_code == 200
        assert response.json()["expected_field"] == "expected_value"
    finally:
        app.dependency_overrides.clear()
```

### 3. 異常系テスト

```python
def test_invalid_data():
    """不正なデータでのエラー"""
    client = TestClient(app)

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        response = client.post("/api/endpoint", json={"invalid": "data"})
        assert response.status_code == 422  # FastAPIのバリデーションエラー
    finally:
        app.dependency_overrides.clear()

def test_not_found():
    """存在しないリソースへのアクセス"""
    client = TestClient(app)

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.family_id = 1

    mock_db_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db_session

    try:
        response = client.get("/api/endpoint/999")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
```

## 🎪 テストフィクスチャの活用

### conftest.py での共通設定

```python
@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_db_session(monkeypatch):
    mock_session = MagicMock()
    from database import db
    monkeypatch.setattr(db, "session", mock_session)
    return mock_session
```

## 📊 アサーション パターン

### 1. HTTPステータスコード

```python
assert response.status_code == 200  # 成功
assert response.status_code == 201  # 作成成功
assert response.status_code == 204  # 成功（レスポンスボディなし）
assert response.status_code == 403  # 未認証（FastAPIデフォルト）
assert response.status_code == 404  # 見つからない、家族スコープ外
assert response.status_code == 409  # 競合（一意制約違反等）
assert response.status_code == 422  # FastAPIバリデーションエラー
```

### 2. レスポンス内容

```python
response_data = response.json()
assert "id" in response_data
assert response_data["field_name"] == expected_value
assert len(response_data["items"]) == expected_count
```

### 3. モック呼び出し確認

```python
mock_function.assert_called_once()
mock_function.assert_called_with(expected_arg)
mock_function.assert_not_called()
```

## 🔐 セキュリティテストパターン

### 1. 権限チェック

```python
def test_admin_only_access(client, monkeypatch):
    """管理者権限が必要な機能のテスト"""
    # 一般ユーザーでアクセス → 403
    # 管理者でアクセス → 200
```

### 2. データスコープ制御

```python
def test_family_scope_isolation(client, monkeypatch):
    """家族スコープでのデータ分離確認"""
    # 異なる家族のデータが見えないことを確認
```

## 📝 テストドキュメント要件

### 1. ファイル冒頭のドキュメント

- API仕様の明確な説明
- テスト観点の体系的な整理
- 全テスト項目の一覧

### 2. 各テスト関数のdocstring

```python
def test_specific_case(client, monkeypatch):
    """具体的なテストケースの説明

    このテストが検証する内容を明確に記述
    """
```

## ⚠️ 重要な注意点

### 1. モック使用時の注意

- **app.dependency_overridesを優先使用**: monkeypatchより推奨
- **try-finally必須**: app.dependency_overrides.clear()を確実に実行
- **データベース操作は必ずモック化**: 実際のDBは使用しない
- **外部API呼び出しはモック化**: HTTPリクエスト等
- **ファイルシステム操作はモック化**: 実際のファイル作成は避ける
- **複雑なクエリチェーンのモック**: JOIN、filter、order_byの順序に注意

### 2. テストデータの管理

- **一意制約を考慮**: user_name, email等の重複回避
- **現実的なデータ**: 実際の使用パターンに近いテストデータ
- **境界値テスト**: 最大長、最小長、空文字等

### 3. テストの独立性

- **テスト間の依存を避ける**: 各テストは独立して実行可能
- **副作用を残さない**: モックのリセット、状態の初期化

### 4. エラーハンドリングテスト

- **想定される全エラーケースをカバー**
- **適切なHTTPステータスコードの確認**
- **エラーメッセージの妥当性確認**

## 📈 テストカバレッジ

### 必須カバレッジ項目

1. **認証・認可**: 全パターン
2. **正常系**: メインフロー
3. **異常系**: 主要なエラーケース
4. **境界値**: データの限界値
5. **セキュリティ**: 権限・スコープ制御

### カバレッジ目標

- **ステートメントカバレッジ**: 90%以上
- **ブランチカバレッジ**: 80%以上
- **重要な機能**: 100%

## 🚀 実装時のベストプラクティス

### 1. テスト設計・実装順序

1. **テストファーストアプローチ**: 実装前にテストケースを設計
2. **段階的実装**: 正常系 → 異常系 → セキュリティテストの順
3. **モック戦略**: `app.dependency_overrides` → 複雑なクエリチェーン → ファイル操作
4. **リファクタリング時**: 既存テストが全て通ることを確認

### 2. HTTPステータスコードの実態把握

- **未認証は403**: FastAPIのデフォルト挙動（401ではない）
- **家族スコープ外は404**: 権限エラーではなく「見つからない」として処理
- **バリデーションエラーは422**: FastAPIの自動バリデーション
- **実装前にAPI仕様確認**: 期待するステータスコードを事前に検証

### 3. モック設計のポイント

- **try-finally必須**: dependency_overridesのクリアを確実に実行
- **家族スコープ**: 他家族データは`None`を返すようモック設計
- **削除済みデータ**: `status=1`フィルタで除外される動作をモック
- **複雑クエリ**: JOIN、filter、order_byのチェーンを個別にモック

### 4. 定期的なメンテナンス

- **テストコードの品質維持**: 実装の変更に合わせてテスト更新
- **ガイドライン更新**: 新しいパターンが発見されたら随時追加

---

このガイドラインに従うことで、一貫性があり保守しやすいテストコードを実装できます。新しいAPIを追加する際は、既存のテストファイルを参考にしながら、このガイドラインに沿って実装してください。