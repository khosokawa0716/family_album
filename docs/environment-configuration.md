# 環境変数設定ガイド

本ドキュメントでは、Family Album アプリケーションの環境変数設定について説明します。

---

## 概要

本アプリケーションは環境変数を使用して、本番環境とローカル開発環境を切り替えることができます。

---

## バックエンド（FastAPI）

### CORS_ORIGINS

CORSで許可するオリジンをカンマ区切りで指定します。

| 環境変数 | 説明 | デフォルト値 |
|---------|------|-------------|
| `CORS_ORIGINS` | 許可するオリジン（カンマ区切り） | `*`（すべて許可） |

**設定例:**

```bash
# 本番環境（特定のドメインのみ許可）
CORS_ORIGINS=http://album.local,https://album.example.com

# ローカル開発（すべて許可）
CORS_ORIGINS=*
# または未設定でもOK
```

**docker-compose.yml での設定:**

```yaml
services:
  api:
    environment:
      - CORS_ORIGINS=http://album.local
```

---

## フロントエンド（Next.js）

### NEXT_PUBLIC_API_BASE

APIエンドポイントのベースURLを指定します。

| 環境変数 | 説明 | デフォルト値 |
|---------|------|-------------|
| `NEXT_PUBLIC_API_BASE` | APIのベースURL | `/api` |

**設定例:**

```bash
# 本番環境（Nginx経由）
NEXT_PUBLIC_API_BASE=/api

# ローカル開発（バックエンド直接）
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
```

**frontend/.env.local での設定（ローカル開発用）:**

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
```

**frontend/.env.production での設定（本番用）:**

```bash
NEXT_PUBLIC_API_BASE=/api
```

---

## 環境別設定例

### 本番環境（Docker Compose）

`docker-compose.yml` または `.env` ファイルで設定:

```yaml
services:
  api:
    environment:
      - CORS_ORIGINS=http://album.local

  frontend:
    environment:
      - NEXT_PUBLIC_API_BASE=/api
```

### ローカル開発環境

**バックエンド単体起動時:**

```bash
# ターミナルで直接起動
CORS_ORIGINS=* uvicorn main:app --reload
```

**フロントエンド単体起動時:**

`frontend/.env.local` を作成:

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
```

---

## 注意事項

- `NEXT_PUBLIC_` プレフィックスが付いた環境変数はクライアントサイドで公開されます
- CORS設定は本番環境では必ず特定のオリジンを指定してください（`*` は非推奨）
- フロントエンドの環境変数はビルド時に埋め込まれるため、変更後は再ビルドが必要です
