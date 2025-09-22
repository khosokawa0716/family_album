-- コメントテーブル作成
CREATE TABLE comments (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    content VARCHAR(1000) NOT NULL,
    user_id INT UNSIGNED NOT NULL,
    picture_id INT UNSIGNED NOT NULL,
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '0: 有効, 1: 削除済み',
    create_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (picture_id) REFERENCES pictures(id),
    INDEX idx_picture_id (picture_id),
    INDEX idx_user_id (user_id),
    INDEX idx_is_deleted (is_deleted),
    INDEX idx_picture_deleted (picture_id, is_deleted),
    INDEX idx_create_date (create_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;