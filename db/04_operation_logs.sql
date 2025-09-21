-- 04_operation_logs.sql
-- operation_logs テーブル作成

CREATE TABLE IF NOT EXISTS `operation_logs` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` INT UNSIGNED NOT NULL,
  `operation` VARCHAR(50) NOT NULL,
  `target_type` VARCHAR(50) NOT NULL,
  `target_id` INT UNSIGNED DEFAULT NULL,
  `detail` TEXT DEFAULT NULL,
  `create_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_operation_logs_user_id` (`user_id`),
  INDEX `idx_operation_logs_operation` (`operation`),
  INDEX `idx_operation_logs_target` (`target_type`, `target_id`),
  INDEX `idx_operation_logs_create_date` (`create_date`),
  CONSTRAINT `fk_operation_logs_user` FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;