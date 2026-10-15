from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

def now() -> datetime: return datetime.now(timezone.utc)

class Repo(Base):
    __tablename__ = "repos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_repo_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(String(255))
    owner: Mapped[str] = mapped_column(String(255))
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    scans: Mapped[list[PRScan]] = relationship(back_populates="repo", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    role: Mapped[str] = mapped_column(String(50), default="viewer")

class RepoAccess(Base):
    __tablename__ = "repo_access"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repos.id", ondelete="CASCADE"), primary_key=True)

class PRScan(Base):
    __tablename__ = "pr_scans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    repo_id: Mapped[int] = mapped_column(ForeignKey("repos.id", ondelete="CASCADE"), index=True)
    pr_number: Mapped[int] = mapped_column(Integer)
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    repo: Mapped[Repo] = relationship(back_populates="scans")
    findings: Mapped[list[Finding]] = relationship(back_populates="scan", cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("pr_scans.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(1024))
    line_number: Mapped[int] = mapped_column(Integer)
    cwe_id: Mapped[str | None] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    snippet: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(128))
    scan: Mapped[PRScan] = relationship(back_populates="findings")
