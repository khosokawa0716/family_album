# db/

## 起動方法

Docker Compose利用時はプロジェクトルートで

```
docker-compose up --build
```

で全サービスが起動します。

DBのみ再起動したい場合：

```
docker-compose restart db
```

---

## 初期化SQL
- `init.sql` などを配置すると初回起動時に自動実行されます

---

詳細はプロジェクトルートの `docs/setup-guide.md` も参照してください。
