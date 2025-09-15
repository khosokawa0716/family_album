-- 03_users.sql
-- users テーブル作成

CREATE TABLE IF NOT EXISTS `users` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_name` VARCHAR(64) NOT NULL,
  `password` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) DEFAULT NULL,
  `type` TINYINT NOT NULL DEFAULT 0,
  `family_id` INT UNSIGNED NOT NULL,
  `status` TINYINT NOT NULL DEFAULT 1,
  `create_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_user_name` (`user_name`),
  UNIQUE KEY `uq_users_email` (`email`),
  CONSTRAINT `fk_users_family` FOREIGN KEY (`family_id`) REFERENCES `Families`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
