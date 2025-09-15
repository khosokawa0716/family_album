-- 00_init_admin.sql
-- 初期データ: デフォルトの families と 管理者ユーザーを投入するスクリプト
-- 注意: 本スクリプトは idempotent（再実行しても重複しない）ように作成しています。
-- パスワードはプレースホルダの bcrypt ハッシュを使っています。実運用では
--  ローカルで bcrypt/argon2 でハッシュを作成してこの値を置き換えてください。

INSERT INTO `families` (`family_name`, `invite_code`, `create_date`, `update_date`)
SELECT 'default-family', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM `families` LIMIT 1);


INSERT INTO `users` (`user_name`, `password`, `email`, `type`, `family_id`, `status`, `create_date`, `update_date`)
SELECT 'admin', '$2b$12$EXAMPLEPLACEHOLDEREXAMPLEPLACEHOLDERE', 'admin@example.com', 10, f.id, 1, NOW(), NOW()
FROM (SELECT id FROM `families` ORDER BY id LIMIT 1) AS f
WHERE NOT EXISTS (SELECT 1 FROM `users` WHERE `user_name` = 'admin');

-- SELECT * FROM `families` LIMIT 1;
-- SELECT id, user_name, email, type, family_id FROM `users` WHERE user_name = 'admin';
