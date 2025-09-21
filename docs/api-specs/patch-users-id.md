# PATCH /api/users/:id - ユーザー情報編集

## 概要
指定されたユーザーIDのユーザー情報を編集するエンドポイント。

## 権限モデル
- **管理者（type=10）**: 全ユーザーの全フィールド編集可能
- **一般ユーザー（type=0）**: 自分自身の基本情報のみ編集可能
  - 編集可能: `user_name`, `email`, `password`
  - 編集不可: `type`, `family_id`, `status`（安全のため）

## リクエスト

### URL
```
PATCH /api/users/{user_id}
```

### Headers
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

### Request Body（UserUpdateスキーマ）
```json
{
  "user_name": "string (optional)",
  "password": "string (optional, 8文字以上)",
  "email": "string (optional, 有効なメール形式)",
  "type": "integer (optional, 0または10, 管理者のみ)",
  "family_id": "integer (optional, 正の整数, 管理者のみ)",
  "status": "integer (optional, 0または1, 管理者のみ)"
}
```

## レスポンス

### 成功時（200 OK）
```json
{
  "id": 1,
  "user_name": "updated_user",
  "email": "updated@example.com",
  "type": 0,
  "family_id": 1,
  "status": 1,
  "create_date": "2023-01-01T00:00:00",
  "update_date": "2023-01-01T00:00:00"
}
```

### エラーレスポンス

#### 400 Bad Request（データ検証エラー）
```json
{
  "detail": "Password must be at least 8 characters long"
}
```

#### 401 Unauthorized（認証失敗）
```json
{
  "detail": "Could not validate credentials"
}
```

#### 403 Forbidden（権限不足）
```json
{
  "detail": "Insufficient permissions. You can only edit your own profile."
}
```

#### 404 Not Found（ユーザーが存在しない）
```json
{
  "detail": "User not found"
}
```

#### 409 Conflict（一意制約違反）
```json
{
  "detail": "Username already exists"
}
```

## データ検証ルール

### 共通ルール
- `user_name`: 空文字禁止
- `password`: 8文字以上（提供された場合のみ更新）
- `email`: 有効なメール形式またはnull
- 一意制約: `user_name`, `email`

### 管理者のみ編集可能
- `type`: 0（一般ユーザー）または10（管理者）
- `family_id`: 正の整数
- `status`: 0（無効）または1（有効）

## 部分更新
- 提供されたフィールドのみ更新
- 提供されないフィールドは既存値を維持
- `password`が提供されない場合、パスワードは変更されない

## セキュリティ仕様
- パスワードは自動的にハッシュ化される
- レスポンスにパスワードは含まれない
- 一般ユーザーは自分以外のユーザー情報にアクセスできない
- 一般ユーザーは権限関連フィールドを変更できない

## 使用例

### 一般ユーザーが自分の情報を編集
```bash
PATCH /api/users/123
Authorization: Bearer {user_token}

{
  "user_name": "new_username",
  "email": "new_email@example.com"
}
```

### 管理者が他ユーザーの権限を変更
```bash
PATCH /api/users/456
Authorization: Bearer {admin_token}

{
  "type": 10,
  "status": 1
}
```

### パスワード変更
```bash
PATCH /api/users/123
Authorization: Bearer {user_token}

{
  "password": "newpassword123"
}
```