from datetime import timedelta
from pathlib import Path

from app.domain.entities.analysis_signal import AnalysisSignal
from app.domain.entities.risk_assessment import RiskAssessment
from app.domain.entities.verification import Verification
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.signal_category import SignalCategory
from app.domain.enums.signal_severity import SignalSeverity
from app.domain.enums.signal_type import SignalType
from app.domain.enums.verdict_type import VerdictType
from app.domain.enums.verification_status import VerificationStatus
from app.domain.services.scoring_policies import BASE_SIGNAL_WEIGHTS
from app.domain.value_objects.confidence_score import ConfidenceScore
from app.domain.value_objects.verification_id import VerificationId
from app.infrastructure.persistence.database import (
    drop_db,
    get_engine,
    get_session_factory,
)
from app.infrastructure.persistence.repositories.sqlalchemy_verification_repository import (
    SQLAlchemyVerificationRepository,
)
from tests.integration.alembic_helpers import upgrade_to_head


def _build_repository(database_path: Path) -> SQLAlchemyVerificationRepository:
    database_url = f"sqlite+pysqlite:///{database_path}"
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    upgrade_to_head(database_url)
    return SQLAlchemyVerificationRepository(get_session_factory(database_url))


def _build_verification(
    verification_id: str,
    created_at_offset_minutes: int = 0,
) -> Verification:
    verification = Verification.create_url(
        "https://secure-paypal-login.example.xyz/verify",
        verification_id=VerificationId.from_string(verification_id),
        calculation_version="v1",
    )
    verification.set_analyzing()
    signal = AnalysisSignal.create(
        signal_type=SignalType.PHISHING_KEYWORDS,
        category=SignalCategory.CONTENT_BEHAVIOR,
        severity=SignalSeverity.HIGH,
        confidence=ConfidenceScore(91),
        title="Credential lure wording in URL",
        description="The URL contains account-action wording.",
        source="url-rule-analyzer",
        base_weight=BASE_SIGNAL_WEIGHTS[SignalType.PHISHING_KEYWORDS],
        evidence=("Matched phishing keywords in the path.",),
        tags=("login", "verify"),
        message_key="signal.credential_lure_wording_in_url",
        message_params={
            "evidence": [
                {
                    "key": "evidence.matched_url_keywords",
                    "params": {"keywords": "login, verify"},
                }
            ]
        },
    )
    verification.add_signal(signal)
    verification.risk_assessment = RiskAssessment(
        score=ConfidenceScore(38),
        risk_level=RiskLevel.HIGH,
        verdict=VerdictType.LIKELY_MALICIOUS,
        summary="High-risk output from persisted repository test fixture.",
        top_signals=(signal.title,),
        category_breakdown={"content_behavior": 44.6},
        terminal_override=False,
        terminal_reason=None,
        calculation_version="v1",
    )
    verification.status = VerificationStatus.COMPLETED
    if created_at_offset_minutes:
        verification.created_at = verification.created_at + timedelta(
            minutes=created_at_offset_minutes
        )
    verification.updated_at = verification.created_at
    verification.completed_at = verification.created_at
    return verification


def test_sqlalchemy_repository_persists_create_get_and_list(tmp_path: Path) -> None:
    database_path = tmp_path / "repository.sqlite3"
    repository = _build_repository(database_path)

    first = _build_verification("550e8400-e29b-41d4-a716-446655440010")
    second = _build_verification(
        "550e8400-e29b-41d4-a716-446655440011", created_at_offset_minutes=1
    )

    repository.save(first)
    repository.save(second)

    fetched = repository.get_by_id(
        VerificationId.from_string("550e8400-e29b-41d4-a716-446655440010")
    )
    assert fetched is not None
    assert fetched.original_input == "https://secure-paypal-login.example.xyz/verify"
    assert fetched.risk_assessment is not None
    assert (
        fetched.risk_assessment.summary
        == "High-risk output from persisted repository test fixture."
    )
    assert fetched.risk_assessment.top_signals == ("Credential lure wording in URL",)
    assert fetched.risk_assessment.category_breakdown == {"content_behavior": 44.6}
    assert fetched.risk_assessment.terminal_override is False
    assert fetched.risk_assessment.terminal_reason is None
    assert fetched.risk_assessment.calculation_version == "v1"
    assert fetched.signals[0].signal_type is SignalType.PHISHING_KEYWORDS
    assert fetched.signals[0].message_key == "signal.credential_lure_wording_in_url"

    listed = repository.list()
    assert [str(item.id) for item in listed] == [
        "550e8400-e29b-41d4-a716-446655440011",
        "550e8400-e29b-41d4-a716-446655440010",
    ]

    drop_db(f"sqlite+pysqlite:///{database_path}")
    get_session_factory.cache_clear()
    get_engine.cache_clear()


def test_sqlalchemy_repository_survives_repository_recreation(tmp_path: Path) -> None:
    database_path = tmp_path / "restart.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path}"

    first_repository = _build_repository(database_path)
    verification = _build_verification("550e8400-e29b-41d4-a716-446655440012")
    first_repository.save(verification)

    get_session_factory.cache_clear()
    get_engine.cache_clear()

    second_repository = SQLAlchemyVerificationRepository(
        get_session_factory(database_url)
    )
    fetched = second_repository.get_by_id(
        VerificationId.from_string("550e8400-e29b-41d4-a716-446655440012")
    )

    assert fetched is not None
    assert fetched.status is VerificationStatus.COMPLETED
    assert fetched.risk_assessment is not None
    assert fetched.risk_assessment.verdict is VerdictType.LIKELY_MALICIOUS
    assert (
        fetched.risk_assessment.summary
        == "High-risk output from persisted repository test fixture."
    )
    assert fetched.risk_assessment.top_signals == ("Credential lure wording in URL",)
    assert fetched.risk_assessment.category_breakdown == {"content_behavior": 44.6}
    assert fetched.risk_assessment.terminal_override is False
    assert fetched.risk_assessment.terminal_reason is None
    assert fetched.risk_assessment.calculation_version == "v1"

    drop_db(database_url)
    get_session_factory.cache_clear()
    get_engine.cache_clear()
