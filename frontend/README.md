# frontend

Next.js (TypeScript) フロントエンド用ディレクトリ。

# frontend/ (Next.js)

## 開発用サーバーの起動方法

Docker Compose利用時はプロジェクトルートで

```
docker-compose up --build
```

で全サービスが起動します。

フロントエンドのみ再起動したい場合：

```
docker-compose restart frontend
```

---

## 直接起動（ローカル開発用）

1. 依存パッケージのインストール
   ```sh
   npm install
   ```
2. 開発サーバー起動
   ```sh
   npm run dev
   ```
3. ブラウザで http://localhost:3000 へアクセス

---

詳細はプロジェクトルートの `docs/setup-guide.md` も参照してください。
