-- 02_families.sql
-- families テーブル作成

CREATE TABLE IF NOT EXISTS `families` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `family_name` VARCHAR(100) NOT NULL,
  `invite_code` VARCHAR(64) DEFAULT NULL,
  `create_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_families_invite_code` (`invite_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
