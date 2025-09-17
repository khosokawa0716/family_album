-- 00_init_admin.sql
-- 初期データ: デフォルトの families と 管理者ユーザーを投入するスクリプト
-- 注意: 本スクリプトは idempotent（再実行しても重複しない）ように作成しています。
-- 環境変数 ADMIN_PASSWORD_HASH と ADMIN_EMAIL を使用します。
-- 実行前に .env ファイルで適切な値を設定してください。

INSERT INTO `families` (`family_name`, `invite_code`, `create_date`, `update_date`)
SELECT 'default-family', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM `families` LIMIT 1);


INSERT INTO `users` (`user_name`, `password`, `email`, `type`, `family_id`, `status`, `create_date`, `update_date`)
SELECT 'admin', '${ADMIN_PASSWORD_HASH}', '${ADMIN_EMAIL}', 10, f.id, 1, NOW(), NOW()
FROM (SELECT id FROM `families` ORDER BY id LIMIT 1) AS f
WHERE NOT EXISTS (SELECT 1 FROM `users` WHERE `user_name` = 'admin');

-- SELECT * FROM `families` LIMIT 1;
-- SELECT id, user_name, email, type, family_id FROM `users` WHERE user_name = 'admin';
