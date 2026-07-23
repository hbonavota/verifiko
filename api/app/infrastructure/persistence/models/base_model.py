from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class VerificationModel(Base):
    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    original_input: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_input: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calculation_version: Mapped[str] = mapped_column(String(32), nullable=False)

    signals: Mapped[list["SignalModel"]] = relationship(
        back_populates="verification",
        cascade="all, delete-orphan",
        order_by="SignalModel.created_at",
    )
    user: Mapped["UserModel | None"] = relationship(back_populates="verifications")
    risk_assessment: Mapped["RiskAssessmentModel | None"] = relationship(
        back_populates="verification",
        cascade="all, delete-orphan",
        uselist=False,
    )


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    google_subject: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="FREE")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    verifications: Mapped[list[VerificationModel]] = relationship(back_populates="user")
    api_keys: Mapped[list["ApiKeyModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class ApiKeyModel(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_used_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["UserModel"] = relationship(back_populates="api_keys")


class MagicLinkTokenModel(Base):
    __tablename__ = "magic_link_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    expires_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class SignalModel(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    message_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    base_weight: Mapped[float] = mapped_column(Float, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    verification: Mapped[VerificationModel] = relationship(back_populates="signals")


class RiskAssessmentModel(Base):
    __tablename__ = "risk_assessments"

    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verifications.id", ondelete="CASCADE"),
        primary_key=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    top_signals: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    category_breakdown: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False, default=dict)
    terminal_override: Mapped[bool] = mapped_column(Boolean, nullable=False)
    terminal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    calculation_version: Mapped[str] = mapped_column(String(32), nullable=False)
    calculated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    verification: Mapped[VerificationModel] = relationship(back_populates="risk_assessment")
