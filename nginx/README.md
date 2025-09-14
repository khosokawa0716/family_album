# nginx/

## 起動方法

Docker Compose利用時はプロジェクトルートで

```
docker-compose up --build
```

で全サービスが起動します。

Nginxのみ再起動したい場合：

```
docker-compose restart nginx
```

---

## 設定ファイル
- `nginx.conf` を編集後は再起動が必要です

---

詳細はプロジェクトルートの `docs/setup-guide.md` も参照してください。
