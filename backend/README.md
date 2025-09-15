# backend

FastAPI バックエンド用ディレクトリ。

# backend/ (FastAPI)

## 開発用サーバーの起動方法

Docker Compose利用時はプロジェクトルートで

```
docker-compose up --build
```

で全サービスが起動します。

バックエンドのみ再起動したい場合：

```
docker-compose restart backend
```

---

## 直接起動（ローカル開発用）

1. 依存パッケージのインストール
   ```sh
   pip3 install -r requirements.txt
   ```

2. 環境変数の設定
   `.env` ファイルを作成し、データベース接続情報を設定：
   ```
   DB_HOST=localhost
   DB_USER=family_album_user
   DB_PASSWORD=your_password
   DB_NAME=family_album
   DB_PORT=3306
   ```

3. 開発サーバー起動
   ```sh
   python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. ブラウザで http://localhost:8000/docs へアクセス（APIドキュメント）

---

詳細はプロジェクトルートの `docs/setup-guide.md` も参照してください。
