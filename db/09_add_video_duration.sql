-- 動画アップロード対応のための duration カラム追加
-- 動画の再生時間（秒）を保持する。画像の場合はNULL。

ALTER TABLE pictures ADD COLUMN duration INT UNSIGNED NULL COMMENT '動画の再生時間（秒）。画像の場合はNULL' AFTER height;
