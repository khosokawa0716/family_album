from sqlalchemy import Column, Integer, String, SmallInteger, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_name = Column(String(64), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    type = Column(SmallInteger, nullable=False, default=0)
    family_id = Column(Integer, nullable=False)
    status = Column(SmallInteger, nullable=False, default=1)
    create_date = Column(DateTime, nullable=False, server_default=func.now())
    update_date = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())