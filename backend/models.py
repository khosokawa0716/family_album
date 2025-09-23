from sqlalchemy import Column, Integer, String, SmallInteger, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_name = Column(String(64), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    type = Column(SmallInteger, nullable=False, default=0)
    family_id = Column(INTEGER(unsigned=True), nullable=False)
    status = Column(SmallInteger, nullable=False, default=1)
    create_date = Column(DateTime, nullable=False, server_default=func.now())
    update_date = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class OperationLog(Base):
    __tablename__ = 'operation_logs'

    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_id = Column(INTEGER(unsigned=True), ForeignKey('users.id'), nullable=False)
    operation = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(INTEGER(unsigned=True))
    detail = Column(Text)
    create_date = Column(DateTime, nullable=False, server_default=func.now())


class Category(Base):
    __tablename__ = 'categories'

    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    family_id = Column(INTEGER(unsigned=True), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(SmallInteger, nullable=False, default=1)
    create_date = Column(DateTime, nullable=False, server_default=func.now())
    update_date = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class Picture(Base):
    __tablename__ = 'pictures'

    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    family_id = Column(INTEGER(unsigned=True), nullable=False)
    uploaded_by = Column(INTEGER(unsigned=True), ForeignKey('users.id'), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500))
    file_size = Column(INTEGER(unsigned=True))
    mime_type = Column(String(100))
    width = Column(INTEGER(unsigned=True))
    height = Column(INTEGER(unsigned=True))
    taken_date = Column(DateTime)
    category_id = Column(INTEGER(unsigned=True), ForeignKey('categories.id'))
    status = Column(SmallInteger, nullable=False, default=1)
    create_date = Column(DateTime, nullable=False, server_default=func.now())
    update_date = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)


class Comment(Base):
    __tablename__ = 'comments'

    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    content = Column(String(1000), nullable=False)
    user_id = Column(INTEGER(unsigned=True), ForeignKey('users.id'), nullable=False)
    picture_id = Column(INTEGER(unsigned=True), ForeignKey('pictures.id'), nullable=False)
    is_deleted = Column(SmallInteger, nullable=False, default=0)
    create_date = Column(DateTime, nullable=False, server_default=func.now())
    update_date = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="comments")