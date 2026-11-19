import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=True, index=True)
    full_name = Column(String(128), nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(16), nullable=False, default="viewer")  # admin|investigator|viewer
    is_active = Column(Boolean, default=True)
    last_login_at = Column(String(32))
    created_at = Column(String(32), default=now_iso)
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    recovery_codes = Column(Text, nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    token_hash = Column(String(64), unique=True, index=True)
    family_id = Column(String(32), index=True)
    expires_at = Column(String(32))
    revoked_at = Column(String(32))
    rotated = Column(Boolean, default=False)


class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True)
    reference = Column(String(64), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    investigator = Column(String(128), default="")
    incident_location = Column(String(200), default="")
    incident_lat = Column(Float, nullable=True)
    incident_lon = Column(Float, nullable=True)
    created_at = Column(String(32), default=now_iso)
    evidence = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    members = relationship("CaseMember", back_populates="case", cascade="all, delete-orphan")


class CaseMember(Base):
    __tablename__ = "case_members"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    role = Column(String(32), default="member")  # member | lead
    added_at = Column(String(32), default=now_iso)
    case = relationship("Case", back_populates="members")
    user = relationship("User")
    __table_args__ = (UniqueConstraint("case_id", "user_id", name="uq_case_user"),)


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"), index=True)
    filename = Column(String(255), nullable=False)
    stored_name = Column(String(128), nullable=False)
    media_type = Column(String(16), nullable=False)
    size = Column(Integer, default=0)
    sha256 = Column(String(64), nullable=False, index=True)
    phash = Column(String(16))
    status = Column(String(16), default="queued")  # queued|analyzing|done|failed
    stage = Column(String(80), default="")
    progress = Column(Integer, default=0)
    error = Column(Text)
    score = Column(Integer)
    verdict = Column(String(24))
    breakdown = Column(Text, default="{}")
    details = Column(Text, default="{}")
    report = Column(Text)
    report_model = Column(String(64))
    review_status = Column(String(16), default="not_reviewed")
    assignee_id = Column(Integer, ForeignKey("users.id"))
    tags = Column(Text, default="[]")
    received_at = Column(String(32), default=now_iso)
    uploaded_by = Column(String(128), default="")
    case = relationship("Case", back_populates="evidence")
    findings = relationship("Finding", back_populates="evidence", cascade="all, delete-orphan",
                            order_by="Finding.id")
    custody = relationship("CustodyEvent", back_populates="evidence", cascade="all, delete-orphan",
                           order_by="CustodyEvent.seq")
    notes = relationship("Note", back_populates="evidence", cascade="all, delete-orphan",
                         order_by="Note.id")

    def get_breakdown(self):
        return json.loads(self.breakdown or "{}")

    def get_details(self):
        return json.loads(self.details or "{}")

    def get_tags(self):
        return json.loads(self.tags or "[]")


class Finding(Base):
    __tablename__ = "findings"
    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), index=True)
    category = Column(String(16))
    check = Column(String(40))
    severity = Column(String(8))  # info|low|medium|high
    penalty = Column(Integer, default=0)
    title = Column(String(200))
    detail = Column(Text)
    location = Column(Text)  # JSON
    feedback = Column(String(16), nullable=True)  # confirmed | rejected
    feedback_by = Column(String(160), nullable=True)
    feedback_at = Column(String(32), nullable=True)
    feedback_note = Column(Text, default="")
    evidence = relationship("Evidence", back_populates="findings")


class CustodyEvent(Base):
    __tablename__ = "custody_events"
    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), index=True)
    seq = Column(Integer, nullable=False)
    action = Column(String(64), nullable=False)
    actor = Column(String(160), nullable=False)
    at = Column(String(32), nullable=False)
    file_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)
    note = Column(Text, default="")
    evidence = relationship("Evidence", back_populates="custody")


class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), index=True)
    author = Column(String(160))
    body = Column(Text)
    created_at = Column(String(32), default=now_iso)
    evidence = relationship("Evidence", back_populates="notes")


class ChatMessage(Base):  # used from Stage 3 (Ask assistant)
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    role = Column(String(12))
    content = Column(Text)
    source = Column(String(64))
    created_at = Column(String(32), default=now_iso)


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    role = Column(String(12), nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    source = Column(String(64), default="")  # "template" | "model" | "glossary" | "search"
    results = Column(Text, default="[]")  # JSON string of structured result cards
    based_on = Column(Text, default="[]")  # JSON string of facts used
    created_at = Column(String(32), default=now_iso)


class ActivityLog(Base):
    __tablename__ = "activity_log"
    id = Column(Integer, primary_key=True)
    at = Column(String(32), default=now_iso, index=True)
    actor = Column(String(160))
    action = Column(String(48), index=True)
    case_id = Column(Integer)
    evidence_id = Column(Integer)
    summary = Column(Text)
    ip = Column(String(64))


class KnownManipulated(Base):
    __tablename__ = "known_manipulated"
    id = Column(Integer, primary_key=True)
    sha256 = Column(String(64), index=True, nullable=True)
    phash = Column(String(64), index=True, nullable=True)
    reason = Column(Text, nullable=False)
    added_by = Column(String(160), default="")
    added_at = Column(String(32), default=now_iso)
    filename = Column(String(255), default="")
    source_evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True)


class ExportedReport(Base):
    __tablename__ = "exported_reports"
    id = Column(Integer, primary_key=True)
    report_sha256 = Column(String(64), unique=True, index=True, nullable=False)
    doc_token = Column(String(64), index=True, nullable=True)
    case_id = Column(Integer, ForeignKey("cases.id"), index=True, nullable=False)
    case_reference = Column(String(64), nullable=False)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=True, index=True)
    report_type = Column(String(32), nullable=False)  # evidence | bundle | section63
    issued_at = Column(String(32), default=now_iso, nullable=False)
    signer_fingerprint = Column(String(128), default="")
