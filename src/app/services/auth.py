"""Локальные аккаунты и отзываемые сессии; секреты хранятся только как хеши."""

import hashlib
import secrets
import time
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from argon2.low_level import Type
from sqlalchemy import case, delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from app.storage.models import AuthRateLimit, AuthSession, User, utcnow

HASHER = PasswordHasher(type=Type.ID)
_DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))
SESSION_SECONDS = 86400


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def csrf_token(token: str) -> str:
    return digest("csrf:" + token)


def normalize_email(email: str) -> str:
    value = email.strip().casefold()
    if len(value) > 320 or value.count("@") != 1 or any(c.isspace() for c in value):
        raise ValueError("Некорректный email")
    if not all(value.split("@")):
        raise ValueError("Некорректный email")
    return value


def validate_password(password: str) -> None:
    if not 12 <= len(password) <= 1024:
        raise ValueError("Пароль должен содержать от 12 до 1024 символов")


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    session_id: UUID
    csrf: str


class AuthService:
    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self.sessions = sessions

    def login(self, email: str, password: str, old_token: str | None) -> tuple[UUID, str] | None:
        with self.sessions.begin() as db:
            user = db.scalar(
                select(User)
                .where(User.email_normalized == normalize_email(email))
                .with_for_update()
            )
            encoded = user.password_hash if user and user.password_hash else _DUMMY_HASH
            valid: bool
            try:
                valid = HASHER.verify(encoded, password)
            except VerificationError:
                valid = False
            if not valid or user is None or user.disabled_at is not None or not user.password_hash:
                return None
            if HASHER.check_needs_rehash(user.password_hash):
                user.password_hash = HASHER.hash(password)
            if old_token:
                db.execute(
                    update(AuthSession)
                    .where(
                        AuthSession.token_hash == digest(old_token),
                        AuthSession.revoked_at.is_(None),
                    )
                    .values(revoked_at=utcnow())
                )
            token = secrets.token_urlsafe(32)
            db.add(
                AuthSession(
                    user_id=user.id,
                    token_hash=digest(token),
                    csrf_secret_hash=digest(csrf_token(token)),
                    expires_at=utcnow() + timedelta(seconds=SESSION_SECONDS),
                )
            )
            return user.id, token

    def authenticate(self, token: str | None) -> Principal | None:
        if not token or len(token) > 128:
            return None
        with self.sessions() as db:
            row = db.scalar(
                select(AuthSession)
                .join(User)
                .where(
                    AuthSession.token_hash == digest(token),
                    AuthSession.revoked_at.is_(None),
                    AuthSession.expires_at > utcnow(),
                    User.disabled_at.is_(None),
                )
            )
            if row is None:
                return None
            csrf = csrf_token(token)
            if not secrets.compare_digest(row.csrf_secret_hash, digest(csrf)):
                return None
            return Principal(row.user_id, row.id, csrf)

    def logout(self, principal: Principal) -> None:
        with self.sessions.begin() as db:
            db.execute(
                update(AuthSession)
                .where(AuthSession.id == principal.session_id)
                .values(revoked_at=utcnow())
            )

    def create_account(self, email: str, password: str) -> UUID:
        validate_password(password)
        with self.sessions.begin() as db:
            user = User(
                email_normalized=normalize_email(email), password_hash=HASHER.hash(password)
            )
            db.add(user)
            db.flush()
            return user.id

    def disable_account(self, email: str) -> None:
        with self.sessions.begin() as db:
            user = db.scalar(
                select(User)
                .where(User.email_normalized == normalize_email(email))
                .with_for_update()
            )
            if user is None:
                raise LookupError("Аккаунт не найден")
            user.disabled_at = utcnow()
            db.execute(
                update(AuthSession)
                .where(AuthSession.user_id == user.id)
                .values(revoked_at=utcnow())
            )

    def rate_limit(self, key: str, limit: int, seconds: int = 60) -> int | None:
        """Атомарный общий fixed-window лимит, включая отклонённые попытки."""
        now = time.time()
        window = int(now // seconds)
        with self.sessions.begin() as db:
            insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
            statement = insert(AuthRateLimit).values(
                key_hash=digest(key), window_no=window, attempts=1
            )
            returning = statement.on_conflict_do_update(
                index_elements=[AuthRateLimit.key_hash],
                set_={
                    "window_no": window,
                    "attempts": case(
                        (AuthRateLimit.window_no == window, AuthRateLimit.attempts + 1), else_=1
                    ),
                },
            ).returning(AuthRateLimit.attempts)
            attempts = db.scalar(returning)
            # Удаляем давно неиспользуемые ключи, ограничивая постоянный рост таблицы.
            db.execute(delete(AuthRateLimit).where(AuthRateLimit.window_no < window - 1440))
        if attempts is not None and attempts > limit:
            return max(1, seconds - int(now % seconds))
        return None
