"""
URL署名ユーティリティ

画像配信用の署名付きURLを生成・検証する機能を提供。
セキュアな画像アクセス制御を実現するため、HMAC-SHA256を使用して
URLに時限付き署名を付与する。

主な機能:
- 署名付きURL生成（有効期限付き）
- URL署名の検証
- 期限切れチェック

使用例:
    # 署名付きURL生成（30分有効）
    signed_url = create_signed_url("thumb_image.jpg", expires_in=1800)

    # 署名検証
    is_valid = verify_url_signature("thumb_image.jpg", signature, expires)
"""

import hmac
import hashlib
import time
from typing import Optional
from urllib.parse import quote, unquote

from config import SECRET_KEY


def create_signed_url(filename: str, endpoint_type: str = "thumbnails", expires_in: int = 1800) -> str:
    """
    署名付きURLを生成する

    Args:
        filename: ファイル名（例: "thumb_image.jpg"）
        endpoint_type: エンドポイントタイプ（"thumbnails" または "photos"）
        expires_in: 有効期限（秒）。デフォルト30分

    Returns:
        str: 署名付きURL（例: "/api/thumbnails/image.jpg?signature=xxx&expires=xxx"）

    Raises:
        ValueError: 無効なendpoint_typeが指定された場合
    """
    if endpoint_type not in ["thumbnails", "photos"]:
        raise ValueError("endpoint_type must be 'thumbnails' or 'photos'")

    # 有効期限のタイムスタンプ（UNIX時間）
    expires = int(time.time()) + expires_in

    # 署名対象データ: "filename:endpoint_type:expires"
    payload = f"{filename}:{endpoint_type}:{expires}"

    # HMAC-SHA256で署名生成
    signature = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    # URL安全な形式でファイル名をエンコード
    safe_filename = quote(filename, safe='.-_')

    return f"/api/{endpoint_type}/{safe_filename}?signature={signature}&expires={expires}"


def verify_url_signature(filename: str, endpoint_type: str, signature: str, expires: int) -> bool:
    """
    URL署名を検証する

    Args:
        filename: ファイル名
        endpoint_type: エンドポイントタイプ（"thumbnails" または "photos"）
        signature: 提供された署名
        expires: 有効期限のタイムスタンプ

    Returns:
        bool: 署名が有効かつ期限内の場合True

    検証項目:
        1. 有効期限チェック
        2. 署名の正当性チェック（timing attack対策でcompare_digest使用）
    """
    # 有効期限チェック
    if time.time() > expires:
        return False

    # 期待される署名を計算
    payload = f"{filename}:{endpoint_type}:{expires}"
    expected_signature = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    # timing attack対策でcompare_digestを使用
    return hmac.compare_digest(signature, expected_signature)


def extract_filename_from_url(url_path: str) -> str:
    """
    URLパスからファイル名を抽出する

    Args:
        url_path: URLパス（例: "/api/thumbnails/thumb_image.jpg"）

    Returns:
        str: ファイル名（例: "thumb_image.jpg"）
    """
    # パスの最後の部分（ファイル名）を取得
    filename = url_path.split('/')[-1]

    # URLデコード
    return unquote(filename)


def get_signature_info(signature: Optional[str], expires: Optional[str]) -> tuple[Optional[str], Optional[int]]:
    """
    クエリパラメータから署名情報を取得・検証する

    Args:
        signature: 署名文字列（クエリパラメータから）
        expires: 有効期限文字列（クエリパラメータから）

    Returns:
        tuple[Optional[str], Optional[int]]: (署名, 有効期限のint) または (None, None)
    """
    if not signature or not expires:
        return None, None

    try:
        expires_int = int(expires)
        return signature, expires_int
    except ValueError:
        return None, None