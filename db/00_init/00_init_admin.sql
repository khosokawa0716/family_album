-- 00_init_admin.sql
-- 初期データ: デフォルトの families と 管理者ユーザーを投入するスクリプト
-- 注意: 本スクリプトは idempotent（再実行しても重複しない）ように作成しています。
--
-- パスワードハッシュ化手順:
-- 1. 以下のPythonコマンドでパスワードをハッシュ化してください:
--    python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your_admin_password'))"
-- 2. 出力されたハッシュ値を下記のINSERT文の password_hash 部分に直接貼り付けてください
-- 3. ADMIN_EMAIL も適切な値に変更してください

INSERT INTO `families` (`family_name`, `invite_code`, `create_date`, `update_date`)
SELECT 'default-family', NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM `families` LIMIT 1);


INSERT INTO `users` (`user_name`, `password`, `email`, `type`, `family_id`, `status`, `create_date`, `update_date`)
SELECT 'admin', 'password_hash', 'example@example.com', 10, f.id, 1, NOW(), NOW()
FROM (SELECT id FROM `families` ORDER BY id LIMIT 1) AS f
WHERE NOT EXISTS (SELECT 1 FROM `users` WHERE `user_name` = 'admin');

-- SELECT * FROM `families` LIMIT 1;
-- SELECT id, user_name, email, type, family_id FROM `users` WHERE user_name = 'admin';
