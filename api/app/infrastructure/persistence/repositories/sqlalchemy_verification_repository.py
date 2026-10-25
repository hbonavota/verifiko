from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload, sessionmaker

from app.domain.entities.verification import Verification
from app.domain.enums.verification_status import VerificationStatus
from app.domain.ports.verification_repository import VerificationRepository
from app.domain.value_objects.user_id import UserId
from app.domain.value_objects.verification_id import VerificationId
from app.infrastructure.persistence.mappers.verification_model_mapper import (
    VerificationModelMapper,
)
from app.infrastructure.persistence.models.base_model import VerificationModel


class SQLAlchemyVerificationRepository(VerificationRepository):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def save(self, verification: Verification) -> Verification:
        with self._session_factory() as session:
            existing = self._get_model(session, verification.id)
            if existing is None:
                model = VerificationModelMapper.to_model(verification)
                session.add(model)
            else:
                VerificationModelMapper.update_model(existing, verification)

            session.commit()
            saved_model = self._get_model(session, verification.id)
            if saved_model is None:
                raise RuntimeError("Verification persistence failed.")
            return VerificationModelMapper.to_domain(saved_model)

    def get_by_id(self, verification_id: VerificationId) -> Verification | None:
        with self._session_factory() as session:
            model = self._get_model(session, verification_id)
            if model is None:
                return None
            return VerificationModelMapper.to_domain(model)

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        status: VerificationStatus | None = None,
    ) -> list[Verification]:
        with self._session_factory() as session:
            statement = (
                select(VerificationModel)
                .options(
                    selectinload(VerificationModel.signals),
                    selectinload(VerificationModel.risk_assessment),
                )
                .order_by(
                    VerificationModel.created_at.desc(),
                    VerificationModel.id.desc(),
                )
                .offset(offset)
                .limit(limit)
            )
            if status is not None:
                statement = statement.where(VerificationModel.status == status.value)

            models = session.execute(statement).scalars().all()
            return [VerificationModelMapper.to_domain(model) for model in models]

    def get_by_id_for_owner(
        self,
        verification_id: VerificationId,
        owner_user_id: UserId,
    ) -> Verification | None:
        with self._session_factory() as session:
            statement = (
                select(VerificationModel)
                .options(
                    selectinload(VerificationModel.signals),
                    selectinload(VerificationModel.risk_assessment),
                )
                .where(
                    VerificationModel.id == str(verification_id),
                    VerificationModel.user_id == str(owner_user_id),
                )
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return VerificationModelMapper.to_domain(model)

    def list_for_owner(
        self,
        owner_user_id: UserId,
        limit: int = 50,
        offset: int = 0,
        status: VerificationStatus | None = None,
    ) -> list[Verification]:
        with self._session_factory() as session:
            statement = (
                select(VerificationModel)
                .options(
                    selectinload(VerificationModel.signals),
                    selectinload(VerificationModel.risk_assessment),
                )
                .where(VerificationModel.user_id == str(owner_user_id))
                .order_by(
                    VerificationModel.created_at.desc(),
                    VerificationModel.id.desc(),
                )
                .offset(offset)
                .limit(limit)
            )
            if status is not None:
                statement = statement.where(VerificationModel.status == status.value)

            models = session.execute(statement).scalars().all()
            return [VerificationModelMapper.to_domain(model) for model in models]

    @staticmethod
    def _get_model(
        session, verification_id: VerificationId
    ) -> VerificationModel | None:
        statement = (
            select(VerificationModel)
            .options(
                selectinload(VerificationModel.signals),
                selectinload(VerificationModel.risk_assessment),
            )
            .where(VerificationModel.id == str(verification_id))
        )
        return session.execute(statement).scalar_one_or_none()
