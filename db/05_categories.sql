-- カテゴリテーブル作成
CREATE TABLE categories (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    family_id INT UNSIGNED NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    status TINYINT NOT NULL DEFAULT 1 COMMENT '1: 有効, 0: 削除済み',
    create_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_family_id (family_id),
    INDEX idx_status (status),
    INDEX idx_family_status (family_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- デフォルトカテゴリ「未分類」の追加
-- NOTE: family_id は1として仮設定。実際の運用では各家族に対して作成が必要
INSERT INTO categories (family_id, name, description, status) VALUES
(1, '未分類', 'カテゴリが設定されていない写真', 1);