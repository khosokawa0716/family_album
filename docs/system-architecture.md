# System Architecture

本システムの全体構成図（バージョン1）

![system-architecture](system-architecture.png)

---

## 概要

- Raspberry Pi 5上で複数コンテナ（Docker）を稼働
- LAN内利用を前提としたセキュアな構成
- 外付けSSDに画像保存、MySQLでメタデータ管理
- Next.js（フロント）、Python API（バックエンド）、Nginx（リバースプロキシ）の三層構成

## コンポーネント

- **Nginx**: リバースプロキシ、アクセス制御
- **Next.js**: フロントエンド、画面レンダリング
- **Python API**: 画像処理、DB/API、認証
- **MySQL**: メタデータ（ユーザー・画像・コメント等）管理
- **外付けSSD**: 画像原本・サムネイル保存
- **Raspberry Pi 5**: 全体のホスト端末

---

## 図（テキスト版）

```
[スマホ/PCブラウザ]
         │
         ▼
      [Nginx]
         │
 ┌───────┴────────┐
 │                 │
▼                 ▼
[Next.js]      [Python API]
   │                │
   │REST API        │画像変換/EXIF/DB
   │                │
   ▼                ▼
               [MySQL]
               [外付けSSD]
```

---

## メモ

- Dockerコンポーズ例やdraw.ioファイルは別途管理可能
- 疑問点や課題についてはREADMEまたは設計メモで管理