# APIエンドポイント一覧（2025/09/13 現在）

本ドキュメントは「家族のアルバム」システムのAPIエンドポイント一覧です。

---

## ユーザー認証・管理
- `POST /api/login` … ログイン
- `POST /api/logout` … ログアウト
- `POST /api/users` … ユーザー新規登録（管理者による登録のみ）
- `GET /api/users/me` … 自分のユーザー情報取得
- `GET /api/users` … ユーザー一覧（管理者のみ）※ページネーション・ソート機能は未実装
- `PATCH /api/users/:id` … ユーザー情報編集（管理者：全フィールド、一般ユーザー：自分のみ基本情報）
- `DELETE /api/users/:id` … ユーザー削除（管理者のみ）

## 写真
- `GET /api/pictures` … 写真一覧（カテゴリ・年月で絞り込み可、無限スクロール対応）
- `GET /api/pictures/:id` … 写真詳細
- `POST /api/pictures` … 写真アップロード
- `DELETE /api/pictures/:id` … 写真削除（ごみ箱へ移動）
- `PATCH /api/pictures/:id/restore` … ごみ箱から復元
- `GET /api/pictures/:id/download` … 原本ダウンロード

## コメント
- `GET /api/pictures/:id/comments` … 写真へのコメント一覧
- `POST /api/pictures/:id/comments` … コメント投稿
- `PATCH /api/comments/:id` … コメント編集
- `DELETE /api/comments/:id` … コメント削除

## カテゴリ
- `GET /api/categories` … カテゴリ一覧
- `POST /api/categories` … カテゴリ追加（管理者のみ）
- `PATCH /api/categories/:id` … カテゴリ編集
- `DELETE /api/categories/:id` … カテゴリ削除

## ごみ箱
- `GET /api/trash` … ごみ箱一覧
- `DELETE /api/trash/:id` … ごみ箱から完全削除
- `PATCH /api/trash/:id/restore` … ごみ箱から復元

## 操作ログ
- `GET /api/logs` … 操作ログ一覧（管理者のみ）

---

※設計・実装により変更の可能性あり。詳細なリクエスト/レスポンス仕様は別途設計書を参照。
