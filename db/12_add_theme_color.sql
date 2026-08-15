-- ユーザーが任意に設定できる表示テーマカラー（プリセットから選択）を追加
-- 未設定/不正値の場合はフロントエンド側でデフォルト（indigo）にフォールバックする。

ALTER TABLE users ADD COLUMN theme_color VARCHAR(20) NULL DEFAULT 'indigo' COMMENT 'プリセットのテーマカラー名（例: indigo, blue, emerald, rose, amber, violet）' AFTER nickname;
