# 画像アップロード実装ガイドライン

## 概要

家族アルバムアプリケーションでの画像アップロード機能における、フロントエンド側の実装ガイドラインです。
バックエンドAPIの制限と連携し、最適なユーザー体験を提供するための指針を示します。

## ファイルサイズ制限設計

### サーバーサイド自動リサイズ

バックエンドで画像を自動的にリサイズするため、ファイルサイズ制限は緩和されています。

| 処理             | 内容                                             |
| ---------------- | ------------------------------------------------ |
| **自動リサイズ** | 長辺2048px超の画像は自動的に2048px以下にリサイズ |
| **回転補正**     | EXIF Orientationに基づく自動回転（iPhone対応）   |
| **HEIC変換**     | HEIC/HEIFは自動的にPNG形式に変換                 |

### フロントエンド制限

| 制限レベル         | 容量制限 | 目的                       |
| ------------------ | -------- | -------------------------- |
| **フロントエンド** | 50MB     | 極端に大きいファイルの除外 |

※ サーバーサイドで自動リサイズされるため、通常は気にする必要はありません。

## 実装例

### 基本的なファイルサイズチェック

```javascript
/**
 * ファイルサイズ検証
 * @param {File} file - 検証対象ファイル
 * @returns {boolean} - 有効かどうか
 */
function validateFileSize(file) {
  const MAX_SIZE = 10 * 1024 * 1024; // 10MB

  if (file.size > MAX_SIZE) {
    showError("画像サイズが大きすぎます。10MB以下のファイルを選択してください。");
    return false;
  }

  return true;
}

// 使用例
const handleFileSelect = (event) => {
  const file = event.target.files[0];

  if (!file) return;

  if (!validateFileSize(file)) {
    event.target.value = ""; // 入力をクリア
    return;
  }

  // アップロード処理を続行
  uploadImage(file);
};
```

### React実装例

```jsx
import React, { useState } from "react";

const ImageUpload = () => {
  const [uploadError, setUploadError] = useState("");

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    setUploadError("");

    if (!file) return;

    // ファイルサイズチェック
    const MAX_SIZE = 10 * 1024 * 1024; // 10MB
    if (file.size > MAX_SIZE) {
      setUploadError(
        "ファイルサイズが10MBを超えています。もう少し小さなファイルを選択してください。",
      );
      event.target.value = "";
      return;
    }

    // ファイル形式チェック
    const allowedTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      setUploadError("JPEG、PNG、GIF、WebP形式の画像ファイルのみアップロード可能です。");
      event.target.value = "";
      return;
    }

    // アップロード処理
    handleUpload(file);
  };

  return (
    <div>
      <input type="file" accept="image/*" onChange={handleFileChange} />
      {uploadError && <div className="error-message">{uploadError}</div>}
    </div>
  );
};
```

### Vue.js実装例

```vue
<template>
  <div>
    <input type="file" accept="image/*" @change="handleFileChange" ref="fileInput" />
    <div v-if="errorMessage" class="error">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      errorMessage: "",
    };
  },
  methods: {
    handleFileChange(event) {
      const file = event.target.files[0];
      this.errorMessage = "";

      if (!file) return;

      // ファイルサイズ検証
      if (!this.validateFile(file)) {
        this.$refs.fileInput.value = "";
        return;
      }

      this.uploadImage(file);
    },

    validateFile(file) {
      const MAX_SIZE = 10 * 1024 * 1024; // 10MB

      if (file.size > MAX_SIZE) {
        this.errorMessage = "ファイルサイズが大きすぎます（最大10MB）";
        return false;
      }

      const allowedTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
      if (!allowedTypes.includes(file.type)) {
        this.errorMessage = "対応していないファイル形式です";
        return false;
      }

      return true;
    },
  },
};
</script>
```

## ユーザー向けメッセージ

### エラーメッセージ例

```javascript
const ERROR_MESSAGES = {
  FILE_TOO_LARGE: "ファイルサイズが大きすぎます。10MB以下のファイルを選択してください。",
  INVALID_FORMAT: "JPEG、PNG、GIF、WebP形式の画像ファイルのみアップロード可能です。",
  NETWORK_ERROR: "アップロードに失敗しました。ネットワーク接続を確認してください。",
  SERVER_ERROR: "サーバーエラーが発生しました。しばらく時間をおいて再試行してください。",
};
```

### ユーザー指導メッセージ

```javascript
const HELP_MESSAGES = {
  SIZE_GUIDANCE:
    "写真のファイルサイズが大きい場合は、スマートフォンの設定で「高効率」形式を選択するか、画像編集アプリで圧縮してください。",
  FORMAT_GUIDANCE: "対応形式: JPEG (.jpg), PNG (.png), GIF (.gif), WebP (.webp)",
  UPLOAD_TIPS: "ヒント: Wi-Fi環境でのアップロードを推奨します。",
};
```

## デバイス別考慮事項

### スマートフォン対応

```javascript
// モバイルデバイス検出
const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
  navigator.userAgent,
);

// モバイル向け制限調整（必要に応じて）
const getMaxFileSize = () => {
  return isMobile ? 8 * 1024 * 1024 : 10 * 1024 * 1024; // モバイル: 8MB, PC: 10MB
};
```

### 高DPI画面対応

```javascript
// 高解像度画面での表示サイズ調整
const getOptimalImageSize = () => {
  const pixelRatio = window.devicePixelRatio || 1;
  return {
    maxWidth: Math.min(2048, window.screen.width * pixelRatio),
    maxHeight: Math.min(2048, window.screen.height * pixelRatio),
  };
};
```

## 将来的な拡張

### Phase 2: 自動画像最適化

```javascript
// 将来実装予定: クライアントサイド画像圧縮
async function compressImage(file, options = {}) {
  const { maxWidth = 2048, maxHeight = 2048, quality = 0.8 } = options;

  // Canvas APIを使用した画像リサイズ・圧縮
  // 実装詳細は別途検討
}
```

### Phase 3: プログレッシブアップロード

```javascript
// 将来実装予定: 段階的品質アップロード
const uploadStrategies = {
  immediate: { quality: 0.6, maxWidth: 1024 }, // 即座アップロード
  background: { quality: 0.9, maxWidth: 2048 }, // バックグラウンド高品質
};
```

## 設定可能な値

```javascript
// 環境設定ファイル例
const UPLOAD_CONFIG = {
  development: {
    maxFileSize: 15 * 1024 * 1024, // 開発環境: 15MB
    allowedTypes: ["image/jpeg", "image/png", "image/gif", "image/webp"],
  },
  production: {
    maxFileSize: 10 * 1024 * 1024, // 本番環境: 10MB
    allowedTypes: ["image/jpeg", "image/png", "image/webp"], // GIF除外検討
  },
};
```

## テスト方針

### ユニットテスト例

```javascript
// Jest テスト例
describe("File Validation", () => {
  test("should reject files larger than 10MB", () => {
    const largeMockFile = new File([""], "large.jpg", {
      type: "image/jpeg",
      size: 11 * 1024 * 1024, // 11MB
    });

    expect(validateFileSize(largeMockFile)).toBe(false);
  });

  test("should accept files smaller than 10MB", () => {
    const normalMockFile = new File([""], "normal.jpg", {
      type: "image/jpeg",
      size: 5 * 1024 * 1024, // 5MB
    });

    expect(validateFileSize(normalMockFile)).toBe(true);
  });
});
```

## まとめ

1. **サーバーサイド自動最適化**
   - 大きい画像は長辺2048px以下に自動リサイズ
   - iPhone等の回転問題を自動補正
   - HEIC/HEIFは自動的にPNGに変換

2. **フロントエンド制限は緩和**
   - 50MB以下であればアップロード可能
   - ユーザーはファイルサイズを気にする必要がない

3. **ユーザー体験の向上**
   - 高画質な元画像をそのまま投稿可能
   - サーバー側で最適化されるため転送後のストレージ使用量は最適化される

**実装優先度: 完了** - サーバーサイドで自動最適化が実装済み

---

_最終更新: 2026-01-25_
_関連API: POST /api/pictures (自動リサイズ: 長辺2048px)_
