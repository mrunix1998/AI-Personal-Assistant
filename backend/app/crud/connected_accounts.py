from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.token_crypto import encrypt_secret
from app.models.connected_account import ConnectedAccount
from app.models.enums import ProviderName, ProviderType


class ConnectedAccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: UUID) -> list[ConnectedAccount]:
        stmt = (
            select(ConnectedAccount)
            .where(ConnectedAccount.user_id == user_id)
            .order_by(ConnectedAccount.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_provider(
        self,
        *,
        user_id: UUID,
        provider_name: ProviderName,
        external_account_id: str | None = None,
    ) -> ConnectedAccount | None:
        stmt = select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.provider_name == provider_name,
        )
        if external_account_id:
            stmt = stmt.where(ConnectedAccount.external_account_id == external_account_id)
        return self.db.scalar(stmt)

    def upsert_google_calendar(
        self,
        *,
        user_id: UUID,
        access_token: str,
        refresh_token: str | None,
        expires_in: int | None,
        external_account_id: str | None = None,
    ) -> ConnectedAccount:
        account = self.get_by_provider(
            user_id=user_id,
            provider_name=ProviderName.GOOGLE_CALENDAR,
            external_account_id=external_account_id,
        )
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        if account is None:
            account = ConnectedAccount(
                user_id=user_id,
                provider_name=ProviderName.GOOGLE_CALENDAR,
                provider_type=ProviderType.CALENDAR,
                external_account_id=external_account_id,
                access_token=encrypt_secret(access_token),
                refresh_token=encrypt_secret(refresh_token),
                token_expires_at=expires_at,
            )
            self.db.add(account)
        else:
            account.access_token = encrypt_secret(access_token)
            if refresh_token:
                account.refresh_token = encrypt_secret(refresh_token)
            account.token_expires_at = expires_at
            if external_account_id:
                account.external_account_id = external_account_id

        self.db.commit()
        self.db.refresh(account)
        return account
