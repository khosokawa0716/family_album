#!/bin/bash
#
# ストレージ設定チェックスクリプト
#
# ボリュームマウントと環境変数の整合性を確認し、
# データ永続化が正しく設定されているかを検証します。
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo " ストレージ設定チェック"
echo "========================================"
echo ""

ERRORS=0

# 1. コンテナが起動しているか確認
echo "[1/4] コンテナ状態を確認中..."
if ! docker compose ps api --format '{{.State}}' 2>/dev/null | grep -q "running"; then
    echo -e "${YELLOW}警告: APIコンテナが起動していません${NC}"
    echo "先に 'docker compose up -d' を実行してください"
    exit 1
fi
echo -e "${GREEN}OK${NC}: APIコンテナは起動中"
echo ""

# 2. 環境変数を確認
echo "[2/4] 環境変数を確認中..."
PHOTOS_PATH=$(docker compose exec -T api printenv PHOTOS_STORAGE_PATH 2>/dev/null || echo "")
THUMBS_PATH=$(docker compose exec -T api printenv THUMBNAILS_STORAGE_PATH 2>/dev/null || echo "")

if [ -z "$PHOTOS_PATH" ]; then
    echo -e "${RED}エラー: PHOTOS_STORAGE_PATH が設定されていません${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo "  PHOTOS_STORAGE_PATH=$PHOTOS_PATH"
fi

if [ -z "$THUMBS_PATH" ]; then
    echo -e "${RED}エラー: THUMBNAILS_STORAGE_PATH が設定されていません${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo "  THUMBNAILS_STORAGE_PATH=$THUMBS_PATH"
fi

# ホストパスが設定されていないか確認（よくある間違い）
if echo "$PHOTOS_PATH" | grep -q "^/media/\|^/mnt/"; then
    echo -e "${RED}エラー: PHOTOS_STORAGE_PATH にホストパスが設定されています${NC}"
    echo "  コンテナ内パス（例: /app/storage/photos）を設定してください"
    ERRORS=$((ERRORS + 1))
fi

if echo "$THUMBS_PATH" | grep -q "^/media/\|^/mnt/"; then
    echo -e "${RED}エラー: THUMBNAILS_STORAGE_PATH にホストパスが設定されています${NC}"
    echo "  コンテナ内パス（例: /app/storage/thumbnails）を設定してください"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 3. ボリュームマウントを確認
echo "[3/4] ボリュームマウントを確認中..."

# テストファイルでマウント確認
TEST_FILE="__storage_test_$(date +%s).tmp"

# 写真ディレクトリのテスト
docker compose exec -T api sh -c "echo 'test' > $PHOTOS_PATH/$TEST_FILE" 2>/dev/null
if [ -f "/media/usbdrive/family_album/photos/$TEST_FILE" ]; then
    echo -e "${GREEN}OK${NC}: 写真ディレクトリはUSBドライブにマウントされています"
    rm -f "/media/usbdrive/family_album/photos/$TEST_FILE"
else
    echo -e "${RED}エラー: 写真ディレクトリがUSBドライブにマウントされていません${NC}"
    echo "  docker-compose.yml の volumes 設定を確認してください"
    ERRORS=$((ERRORS + 1))
fi
docker compose exec -T api rm -f "$PHOTOS_PATH/$TEST_FILE" 2>/dev/null || true

# サムネイルディレクトリのテスト
docker compose exec -T api sh -c "echo 'test' > $THUMBS_PATH/$TEST_FILE" 2>/dev/null
if [ -f "/media/usbdrive/family_album/thumbnails/$TEST_FILE" ]; then
    echo -e "${GREEN}OK${NC}: サムネイルディレクトリはUSBドライブにマウントされています"
    rm -f "/media/usbdrive/family_album/thumbnails/$TEST_FILE"
else
    echo -e "${RED}エラー: サムネイルディレクトリがUSBドライブにマウントされていません${NC}"
    echo "  docker-compose.yml の volumes 設定を確認してください"
    ERRORS=$((ERRORS + 1))
fi
docker compose exec -T api rm -f "$THUMBS_PATH/$TEST_FILE" 2>/dev/null || true
echo ""

# 4. ホストディレクトリの権限確認
echo "[4/4] ディレクトリ権限を確認中..."
if [ -w "/media/usbdrive/family_album/photos" ]; then
    echo -e "${GREEN}OK${NC}: /media/usbdrive/family_album/photos は書き込み可能"
else
    echo -e "${RED}エラー: /media/usbdrive/family_album/photos に書き込めません${NC}"
    ERRORS=$((ERRORS + 1))
fi

if [ -w "/media/usbdrive/family_album/thumbnails" ]; then
    echo -e "${GREEN}OK${NC}: /media/usbdrive/family_album/thumbnails は書き込み可能"
else
    echo -e "${RED}エラー: /media/usbdrive/family_album/thumbnails に書き込めません${NC}"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# 結果サマリー
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}チェック完了: すべて正常です${NC}"
    echo "写真とサムネイルはUSBドライブに永続化されます"
    exit 0
else
    echo -e "${RED}チェック完了: $ERRORS 件のエラーがあります${NC}"
    echo ""
    echo "解決方法:"
    echo "1. docker-compose.yml の environment と volumes を確認"
    echo "2. docs/production-deployment-guide.md の"
    echo "   「重要: ストレージ設定について」セクションを参照"
    exit 1
fi
