import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
# 家族専用アプリのため、LINE通知経由のアクセス等を考慮して長めに設定（7日間）
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7