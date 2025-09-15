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

## ローカルMySQL構築

1. MySQLのインストール
   ```sh
   brew install mysql
   ```

2. MySQLサービスの開始
   ```sh
   brew services start mysql
   ```

3. MySQLにログイン
   ```sh
   mysql -u root -p
   ```

4. データベースとユーザーの作成
   ```sql
   CREATE DATABASE family_album;
   CREATE USER 'family_album_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON family_album.* TO 'family_album_user'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

5. 初期化SQLの実行（もしあれば）
   ```sh
   mysql -u family_album_user -p family_album < init.sql
   ```

---

## 初期化SQL
- `init.sql` などを配置すると初回起動時に自動実行されます

---

詳細はプロジェクトルートの `docs/setup-guide.md` も参照してください。
