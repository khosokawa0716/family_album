-- 写真グループ化のための group_id カラム追加
-- 複数枚同時投稿された写真を同じ group_id でグループ化する

-- Step 1: nullable で group_id カラムを追加
ALTER TABLE pictures ADD COLUMN group_id CHAR(36) NULL AFTER uploaded_by;

-- Step 2: 既存の写真に個別の UUID を割り当て（1枚1グループ）
UPDATE pictures SET group_id = UUID() WHERE group_id IS NULL;

-- Step 3: NOT NULL 制約を適用
ALTER TABLE pictures MODIFY COLUMN group_id CHAR(36) NOT NULL;

-- Step 4: インデックス追加
CREATE INDEX idx_group_id ON pictures (group_id);
CREATE INDEX idx_family_group ON pictures (family_id, group_id);
