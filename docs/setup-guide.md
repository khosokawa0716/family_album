# 開発環境・立ち上げ手順（Docker Compose版）

本ドキュメントは「家族のアルバム」開発環境の初期セットアップ手順です。

---

## 前提条件
- Docker, Docker Compose がインストール済みであること
- git で本リポジトリをクローン済みであること

---

## ディレクトリ構成（主要部分）

```
frontend/         # Next.js (TypeScript)
backend/          # FastAPI (Python)
nginx/            # Nginxリバースプロキシ
 db/              # MySQLデータ永続化・初期化
 docker-compose.yml
```

---

## 1. 環境変数の設定（初回のみ）

必要に応じて `.env` ファイルをルートや各サービス配下に作成してください。

---

## 2. Dockerイメージのビルド＆起動

プロジェクトルートで以下を実行：

```sh
docker-compose up --build
```

- 初回はイメージのビルドに数分かかります
- 起動後、各サービスは以下のポートでアクセス可能です
  - フロントエンド: http://localhost:3000
  - バックエンドAPI: http://localhost:8000
  - Nginx: http://localhost (リバースプロキシ)
  - MySQL: localhost:3306

---

## 3. DB初期化（必要な場合）

`db/init.sql` などに初期データ投入用SQLを用意し、docker-compose起動時に自動実行されます。

---

## 4. サービスの個別操作

- フロントエンドのみ再起動：
  ```sh
  docker-compose restart frontend
  ```
- バックエンドのみ再起動：
  ```sh
  docker-compose restart backend
  ```

---

## 5. その他
- 停止：`docker-compose down`
- ボリュームも削除：`docker-compose down -v`
- ログ確認：`docker-compose logs -f <サービス名>`

---

## 補足
- 本番運用時はNginxのSSL設定やDBバックアップ等を追加してください
- 詳細な開発手順やAPI仕様は他のドキュメントを参照
