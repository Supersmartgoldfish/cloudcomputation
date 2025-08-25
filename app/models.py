# app/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)

class Host(Base):
    __tablename__ = "hosts"
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(String, unique=True, index=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    specs = Column(JSON, default={})
    network = Column(JSON, default={})
    installed_apps = Column(JSON, default=[])
    available = Column(Boolean, default=True)
    grade = Column(Float, default=0.0)
    pay_rate = Column(Float, default=0.0)
    last_seen = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", backref="hosts")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    host_id = Column(Integer, ForeignKey("hosts.id"), nullable=True)
    app = Column(String)
    payload = Column(JSON, default={})  # job parameters, docker image, etc.
    status = Column(String, default="pending")  # pending, running, done, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    earned = Column(Float, default=0.0)

class SessionRecord(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    host_id = Column(Integer, ForeignKey("hosts.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_hours = Column(Float, default=0.0)
    payout = Column(Float, default=0.0)
