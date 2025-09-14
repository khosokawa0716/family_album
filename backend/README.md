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
   pip install -r requirements.txt
   ```
2. 開発サーバー起動
   ```sh
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
3. ブラウザで http://localhost:8000/docs へアクセス（APIドキュメント）

---

詳細はプロジェクトルートの `docs/setup-guide.md` も参照してください。
