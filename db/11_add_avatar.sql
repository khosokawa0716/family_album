-- ユーザーが任意に設定できるプロフィール画像（アバター）の保存パスを追加
-- 未設定の場合はNULLとなり、表示時はイニシャルアバターにフォールバックする。

ALTER TABLE users ADD COLUMN avatar_path VARCHAR(500) NULL COMMENT 'プロフィール画像の保存パス（未設定時はイニシャルアバターを表示）' AFTER nickname;
