from datetime import datetime
import json
from sqlalchemy import Column, String, Text, DateTime, Boolean, Float, Enum as SQLEnum
from app.db.database import Base
from app.schemas.domain import DraftStatus


class ContextSection(Base):
    __tablename__ = "context_sections"

    ref = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    document_name = Column(String, nullable=False, default="product_brief.md")
    updated_at = Column(DateTime, default=datetime.utcnow)


class BacklogItemModel(Base):
    __tablename__ = "backlog_items"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    acceptance_criteria = Column(Text, default="")
    citations = Column(Text, default="[]")  # JSON string
    status = Column(String, default="NOT_READY")
    created_at = Column(DateTime, default=datetime.utcnow)


class DraftModel(Base):
    __tablename__ = "drafts"

    id = Column(String, primary_key=True, index=True)
    item_type = Column(String, nullable=False)  # "STORY" or "CRITERIA"
    title = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(SQLEnum(DraftStatus), default=DraftStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApprovalLogModel(Base):
    __tablename__ = "approval_log"

    id = Column(String, primary_key=True, index=True)
    draft_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)  # "APPROVED" or "REJECTED"
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class WriteLogModel(Base):
    __tablename__ = "write_log"

    id = Column(String, primary_key=True, index=True)
    draft_id = Column(String, nullable=False)
    external_item_id = Column(String, nullable=False)
    target_system = Column(String, nullable=False, default="MockTracker")
    tags = Column(Text, default="[]")  # JSON list
    status = Column(String, nullable=False, default="NOT_READY")
    timestamp = Column(DateTime, default=datetime.utcnow)
