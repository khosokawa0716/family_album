# family_album

## 1. アプリ名
- 家族のアルバム

## 2. 目的
- 家族内で写真を安全に共有・閲覧・コメントできるようにする（自宅LAN内運用）

## 10. ローカル開発環境立ち上げメモ

### データベース (MySQL)
```bash
# 状態確認
brew services list

# 開始
brew services start mysql

# 停止
brew services stop mysql
```

### nginx
```bash
# 状態確認
brew services list

# 開始
brew services start nginx

# 停止
brew services stop nginx
```

### バックエンド
```bash
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- 直接アクセス: http://localhost:8000/
- nginx経由: http://localhost:8080/api

### フロントエンド
```bash
npm run dev
```
- 直接アクセス: http://localhost:3000/
- nginx経由: http://localhost:8080/