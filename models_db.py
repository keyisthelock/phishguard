"""Relational entities; existing users/scans schema remains unchanged."""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow(): return datetime.now(timezone.utc).replace(tzinfo=None)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__='users'
    id: Mapped[int]=mapped_column(primary_key=True)
    username: Mapped[str]=mapped_column(String(60),unique=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    role: Mapped[str]=mapped_column(String(10),default='user')
class Scan(Base):
    __tablename__='scans'
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    message: Mapped[str]=mapped_column(Text)
    result: Mapped[str]=mapped_column(Text)
    label: Mapped[str]=mapped_column(String(30),index=True)
    score: Mapped[int]=mapped_column(Integer)
    language: Mapped[str]=mapped_column(String(15))
    created_at: Mapped[datetime]=mapped_column(DateTime,default=utcnow,index=True)
class DetectionResult(Base):
    __tablename__='detection_results'
    scan_id: Mapped[int]=mapped_column(ForeignKey('scans.id'),primary_key=True)
    mode: Mapped[str]=mapped_column(String(12),default='message')
    ml_score: Mapped[int | None]=mapped_column(Integer,nullable=True)
    rule_score: Mapped[int]=mapped_column(Integer)
    model_version: Mapped[str]=mapped_column(String(40),default='sms-lr-v1')
class WarningIndicator(Base):
    __tablename__='warning_indicators'
    id: Mapped[int]=mapped_column(primary_key=True)
    scan_id: Mapped[int]=mapped_column(ForeignKey('scans.id'),index=True)
    description: Mapped[str]=mapped_column(String(255))
class Feedback(Base):
    __tablename__='feedback'
    scan_id: Mapped[int]=mapped_column(ForeignKey('scans.id'),primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    verdict: Mapped[str]=mapped_column(String(30))
    note: Mapped[str]=mapped_column(String(400),default='')
    reviewed: Mapped[int]=mapped_column(Integer,default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=utcnow)
class SchemaVersion(Base):
    __tablename__='schema_versions'
    version: Mapped[int]=mapped_column(primary_key=True)
    applied_at: Mapped[datetime]=mapped_column(DateTime,default=utcnow)
