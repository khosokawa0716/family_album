import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# 環境変数からデータベース接続情報を取得
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "family_album_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")
DB_NAME = os.getenv("DB_NAME", "family_album")
DB_PORT = os.getenv("DB_PORT", "3306")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemyエンジンの作成
engine = create_engine(DATABASE_URL)

# セッションの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラス
Base = declarative_base()

class Database:
    def __init__(self):
        self.engine = engine
        self.session = SessionLocal()

    def execute(self, query):
        return self.session.execute(text(query))

    def close(self):
        self.session.close()

# インスタンスを作成
db = Database()