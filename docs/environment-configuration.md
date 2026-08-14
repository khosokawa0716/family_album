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

### LINE_CHANNEL_ACCESS_TOKEN

新着投稿（写真・動画アップロード）時に、LINE公式アカウントの友だち全員へブロードキャスト通知するためのチャネルアクセストークンです。

| 環境変数 | 説明 | デフォルト値 |
|---------|------|-------------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging APIのチャネルアクセストークン（長期） | 未設定（通知はスキップされる） |

未設定の場合は通知処理自体がスキップされ、アップロードAPIの処理には影響しません。

**設定例:**

```bash
LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### FRONTEND_URL

LINE通知本文に含める詳細ページ（`/photo/detail/{group_id}`）のURLを組み立てるための、フロントエンドの公開URLです。

| 環境変数 | 説明 | デフォルト値 |
|---------|------|-------------|
| `FRONTEND_URL` | フロントエンドの公開URL（末尾スラッシュなし推奨） | 未設定（通知本文にURLを含めない） |

未設定の場合は通知処理自体はスキップされず、メッセージ本文からURLの行が省かれるだけです。

**設定例:**

```bash
# 本番環境（Raspberry PiへのmDNS接続を前提）
FRONTEND_URL=http://album.local

# ローカル開発
FRONTEND_URL=http://localhost:3000
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
      - FRONTEND_URL=http://album.local

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
