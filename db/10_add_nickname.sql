-- ユーザーが任意に設定できる表示用ニックネームを追加
-- 未設定の場合はNULLとなり、表示時はuser_nameにフォールバックする。

ALTER TABLE users ADD COLUMN nickname VARCHAR(64) NULL COMMENT '表示用ニックネーム（未設定時はuser_nameを表示）' AFTER user_name;
