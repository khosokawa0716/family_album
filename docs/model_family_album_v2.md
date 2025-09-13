# Family Album ER図（バージョン2・提案）

---

## Families

| カラム名      | 型             | 制約             | 説明         |
|--------------|----------------|------------------|--------------|
| id           | int            | PK, AUTO_INCREMENT | 家族ID       |
| family_name  | varchar(100)   | NOT NULL         | 家族の名前   |
| invite_code  | varchar(64)    | UNIQUE           | 招待コード * 立ち上げ時使用しない |
| create_date  | datetime       | NOT NULL         | 作成日時     |
| update_date  | datetime       | NOT NULL         | 更新日時     |

---

## Users

| カラム名      | 型             | 制約                | 説明               |
|--------------|----------------|---------------------|--------------------|
| id           | int            | PK, AUTO_INCREMENT  | ユーザーID         |
| user_name    | varchar(64)    | NOT NULL, UNIQUE    | ユーザー名         |
| password     | varchar(255)   | NOT NULL            | パスワード(ハッシュ)|
| email        | varchar(255)   | UNIQUE              | メールアドレス     |
| type         | tinyint        | NOT NULL, default:0 | ユーザー種別 0: 一般ユーザー、10: 管理者   |
| family_id    | int            | NOT NULL, FK        | 家族ID（外部キー） |
| status       | tinyint        | NOT NULL, default:1 | ステータス  * 立ち上げ時使用しない  |
| create_date  | datetime       | NOT NULL            | 作成日時           |
| update_date  | datetime       | NOT NULL            | 更新日時           |

---

## Categories

| カラム名      | 型             | 制約                     | 説明               |
|--------------|----------------|--------------------------|--------------------|
| id           | int            | PK, AUTO_INCREMENT       | カテゴリID         |
| category_name| varchar(64)    | NOT NULL                 | カテゴリ名         |
| display_order| int            | NOT NULL, default:0      | 表示順             |
| family_id    | int            | NOT NULL, FK             | 家族ID（外部キー） |
| is_deleted   | tinyint        | NOT NULL, default:0      | 論理削除フラグ     |
| create_date  | datetime       | NOT NULL                 | 作成日時           |
| update_date  | datetime       | NOT NULL                 | 更新日時           |

---

## Pictures

| カラム名        | 型             | 制約                         | 説明                     |
|----------------|----------------|------------------------------|--------------------------|
| id             | int            | PK, AUTO_INCREMENT           | 画像ID                   |
| image_path     | varchar(255)   | NOT NULL                     | 画像ファイルパス         |
| display_order  | int            | NOT NULL, default:0          | 表示順                   |
| user_id        | int            | NOT NULL, FK                 | 投稿ユーザーID           |
| category_id    | int            | FK                           | カテゴリID（外部キー）   |
| is_deleted     | tinyint        | NOT NULL, default:0          | 論理削除フラグ           |
| allow_download | tinyint        | NOT NULL, default:0          | ダウンロード許可         |
| delete_date    | datetime       |                              | 削除日時                 |
| create_date    | datetime       | NOT NULL                     | 作成日時                 |
| update_date    | datetime       | NOT NULL                     | 更新日時                 |

---

## Comments

| カラム名      | 型             | 制約                     | 説明                 |
|--------------|----------------|--------------------------|----------------------|
| id           | int            | PK, AUTO_INCREMENT       | コメントID           |
| content      | varchar(1000)  | NOT NULL                 | コメント内容         |
| user_id      | int            | NOT NULL, FK             | 投稿ユーザーID       |
| picture_id   | int            | NOT NULL, FK             | 画像ID（外部キー）   |
| is_deleted   | tinyint        | NOT NULL, default:0      | 論理削除フラグ       |
| create_date  | datetime       | NOT NULL                 | 作成日時             |
| update_date  | datetime       | NOT NULL                 | 更新日時             |

---

## OperationLogs

| カラム名      | 型             | 制約                | 説明                       |
|--------------|----------------|---------------------|----------------------------|
| id           | int            | PK, AUTO_INCREMENT  | ログID                     |
| user_id      | int            | NOT NULL, FK        | 操作ユーザーID             |
| operation    | varchar(50)    | NOT NULL            | 操作内容（CREATE等）       |
| target_type  | varchar(50)    | NOT NULL            | 対象種別（picture等）      |
| target_id    | int            |                      | 対象ID                     |
| detail       | text           |                      | 詳細（任意）               |
| create_date  | datetime       | NOT NULL            | 操作日時                   |

---

## Trash

| カラム名      | 型             | 制約                | 説明                       |
|--------------|----------------|---------------------|----------------------------|
| id           | int            | PK, AUTO_INCREMENT  | ゴミ箱ID                   |
| item_type    | varchar(50)    | NOT NULL            | 種別（picture, comment等） |
| item_id      | int            | NOT NULL            | 元データID                 |
| user_id      | int            | NOT NULL, FK        | 削除ユーザーID             |
| delete_date  | datetime       | NOT NULL            | 削除日時                   |
| restore_code | varchar(64)    |                      | 復元用コード等             |

---

## テーブル間リレーション

- **Users.family_id → Families.id** （多対1, 外部キー）
- **Categories.family_id → Families.id** （多対1, 外部キー）
- **Pictures.user_id → Users.id**（多対1, 外部キー）
- **Pictures.category_id → Categories.id**（多対1, 外部キー, NULL可）
- **Comments.picture_id → Pictures.id**（多対1, 外部キー）
- **Comments.user_id → Users.id**（多対1, 外部キー）
- **OperationLogs.user_id → Users.id**（多対1, 外部キー）
- **Trash.user_id → Users.id**（多対1, 外部キー）

---

## 運用ルール・注記

- **UNIQUE制約**: user_name, email, invite_code
- **外部キー制約（FK）**: RDBMS上で必ず設定すること
- **is_deleted, allow_download, display_order** などは `NOT NULL DEFAULT 0` を推奨
- **親（Picture）が論理削除された場合、紐づくCommentも論理削除する**
- **Familiesテーブルで家族単位の管理が可能**
- **Trashは論理削除フラグ＋一時保存用のテーブルとしてごみ箱機能を実現**
- **OperationLogsで監査ログや操作履歴を保存**
- **invite_codeは家族招待時の一意なコード（有効期限や利用済み管理は今後の拡張で対応）**

---

## 補足

- 追加のテーブルや運用ルールがあれば、追記・修正も可能です。