"""Сессии, CSRF и изоляция пользователей на настоящих репозиториях."""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.pool import StaticPool
from tests.integration import test_repositories

from app.api.auth import COOKIE_NAME, AuthSettings, owned_conversation, require_owner
from app.auth_cli import main as account_cli
from app.main import create_app
from app.services.auth import AuthService, Principal, digest
from app.storage.models import AuthRateLimit, AuthSession, Conversation, User, utcnow
from app.storage.repositories import OwnedRepository, make_session_factory

PASSWORD = "synthetic-password-for-tests"
ORIGIN = "https://app.example.test"
CONFIG = AuthSettings(origins=(ORIGIN,))
pg_engine = test_repositories.engine


@pytest.fixture
def service():  # type: ignore[no-untyped-def]
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for model in (User, AuthSession, AuthRateLimit):
        model.__table__.create(engine)
    auth = AuthService(make_session_factory(engine))
    auth.create_account("alice@example.test", PASSWORD)
    auth.create_account("bob@example.test", PASSWORD)
    yield auth
    engine.dispose()


def client_for(service: AuthService, config: AuthSettings = CONFIG) -> TestClient:
    return TestClient(create_app(auth=service, auth_settings=config), base_url=ORIGIN)


def login(client: TestClient, email: str = "alice@example.test") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200, response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]
    return response.json()  # type: ignore[no-any-return]


def test_session_rotation_csrf_logout(service: AuthService) -> None:
    client = client_for(service)
    first = login(client, " ALICE@EXAMPLE.TEST ")
    old = client.cookies.get(COOKIE_NAME)
    assert client.get("/api/v1/auth/session").json() == first
    second = login(client)
    token = client.cookies.get(COOKIE_NAME)
    assert token != old and first["csrf_token"] != second["csrf_token"]
    assert service.authenticate(old) is None
    for headers in (
        {"Origin": ORIGIN},
        {"Origin": ORIGIN, "X-CSRF-Token": "invalid"},
        {"Origin": "https://evil.test", "X-CSRF-Token": second["csrf_token"]},
    ):
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/v1/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": second["csrf_token"]}
        ).status_code
        == 204
    )
    assert service.authenticate(token) is None
    assert client.get("/api/v1/auth/session").status_code == 401
    with service.sessions() as db:
        rows = list(db.scalars(select(AuthSession)))
        assert all(r.revoked_at is not None for r in rows)
        assert all(r.token_hash not in {old, token} for r in rows)
        assert all(r.csrf_secret_hash != second["csrf_token"] for r in rows)
        assert db.scalar(select(User.password_hash)).startswith("$argon2id$")


@pytest.mark.parametrize("email", ["missing@example.test", "alice@example.test"])
def test_bad_credentials(service: AuthService, email: str) -> None:
    response = client_for(service).post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": "secret-sentinel"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert "secret-sentinel" not in response.text
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("origin", [None, "null", "https://evil.test", ORIGIN + "/"])
def test_login_origin(service: AuthService, origin: str | None) -> None:
    headers = {"Origin": origin} if origin else {}
    response = client_for(service).post(
        "/api/v1/auth/login",
        headers=headers,
        json={"email": "alice@example.test", "password": PASSWORD},
    )
    assert response.status_code == 403


def test_expiry_disable_and_forgery(service: AuthService) -> None:
    alice, bob = client_for(service), client_for(service)
    login(alice)
    login(bob, "bob@example.test")
    with service.sessions.begin() as db:
        db.execute(
            update(AuthSession)
            .where(AuthSession.token_hash == digest(alice.cookies.get(COOKIE_NAME)))
            .values(expires_at=utcnow() - timedelta(seconds=1))
        )
    assert alice.get("/api/v1/auth/session").status_code == 401
    service.disable_account("bob@example.test")
    assert bob.get("/api/v1/auth/session").status_code == 401
    assert (
        bob.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"email": "bob@example.test", "password": PASSWORD},
        ).status_code
        == 401
    )
    assert service.authenticate("forged") is None


def test_http_requires_opt_in(service: AuthService) -> None:
    client = TestClient(
        create_app(auth=service, auth_settings=CONFIG), base_url="http://testserver"
    )
    assert client.get("/api/v1/auth/session").status_code == 403
    with pytest.raises(ValueError):
        AuthSettings(cookie_secure=False)
    config = AuthSettings(
        origins=("http://testserver",), http_dev_enabled=True, cookie_secure=False
    )
    client = TestClient(
        create_app(auth=service, auth_settings=config), base_url="http://testserver"
    )
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "http://testserver"},
        json={"email": "alice@example.test", "password": PASSWORD},
    )
    assert response.status_code == 200
    assert "Secure" not in response.headers["set-cookie"]
    assert client.get("/api/v1/auth/session").status_code == 200


@pytest.mark.parametrize("kind", ["login_ip", "login_account", "request_ip", "request_user"])
def test_rate_limits(service: AuthService, kind: str) -> None:
    config = replace(CONFIG, **{kind + "_limit": 1})
    client = client_for(service, config)
    login(client)
    if kind.startswith("login"):
        other = client_for(AuthService(service.sessions), config)
        response = other.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"email": "alice@example.test", "password": PASSWORD},
        )
    else:
        assert client.get("/api/v1/auth/session").status_code == 200
        response = client.get("/api/v1/auth/session")
    assert response.status_code == 429
    assert 1 <= int(response.headers["retry-after"]) <= 60


def test_invalid_envelope_never_echoes_password(service: AuthService) -> None:
    client = client_for(service)
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": "alice@example.test", "password": {"secret": "sentinel"}},
    )
    assert response.status_code == 422 and "sentinel" not in response.text
    response = client.post("/api/v1/auth/login", headers={"Origin": ORIGIN}, content="x" * 8193)
    assert response.status_code == 413


def test_operator_cli(tmp_path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    url = "sqlite:///" + str(tmp_path / "accounts.db")
    engine = create_engine(url)
    for model in (User, AuthSession, AuthRateLimit):
        model.__table__.create(engine)
    service = AuthService(make_session_factory(engine))
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr("getpass.getpass", lambda _: PASSWORD)
    monkeypatch.setattr(sys, "argv", ["auth_cli", "create", "operator@example.test"])
    account_cli()
    result = service.login("operator@example.test", PASSWORD, None)
    assert result is not None
    monkeypatch.setattr(sys, "argv", ["auth_cli", "disable", "operator@example.test"])
    account_cli()
    assert service.authenticate(result[1]) is None
    assert PASSWORD not in capsys.readouterr().out
    engine.dispose()


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="no PostgreSQL test DB")
def test_repository_and_protected_route(pg_engine) -> None:  # type: ignore[no-untyped-def] # noqa: F811
    service = AuthService(make_session_factory(pg_engine))
    alice_id = service.create_account("alice@example.test", PASSWORD)
    bob_id = service.create_account("bob@example.test", PASSWORD)
    conversation_id = uuid4()
    with service.sessions.begin() as db:
        db.add(Conversation(id=conversation_id, owner_user_id=alice_id))
    app = create_app(auth=service, auth_settings=CONFIG)

    @app.get("/test/conversations/{conversation_id}")
    def protected(
        conversation_id: UUID, principal: Annotated[Principal, Depends(require_owner)]
    ) -> dict[str, str]:
        with service.sessions() as db:
            row = owned_conversation(db, principal, conversation_id)
            return {"id": str(row.id)}

    alice, bob = TestClient(app, base_url=ORIGIN), TestClient(app, base_url=ORIGIN)
    login(alice)
    login(bob, "bob@example.test")
    assert alice.get(f"/test/conversations/{conversation_id}").status_code == 200
    чужой = bob.get(f"/test/conversations/{conversation_id}")
    неизвестный = bob.get(f"/test/conversations/{uuid4()}")
    assert чужой.status_code == неизвестный.status_code == 404
    assert чужой.json()["error"]["code"] == неизвестный.json()["error"]["code"]
    with service.sessions.begin() as db:
        repo = OwnedRepository(db)
        assert repo.conversation(bob_id, conversation_id) is None
        run, _ = repo.accept_run(
            owner_id=alice_id,
            conversation_id=conversation_id,
            idempotency_key="auth-test",
            request_hash="a" * 64,
            expected_idea_version=0,
            content="test",
            query="test",
        )
        assert repo.get_run(run.id, owner_id=bob_id) is None
        assert repo.get_message(run.message_id, owner_id=bob_id) is None
        assert repo.evidence(run.id, owner_id=bob_id) == []
        with pytest.raises(LookupError):
            repo.accept_run(
                owner_id=bob_id,
                conversation_id=conversation_id,
                idempotency_key="auth-test",
                request_hash="a" * 64,
                expected_idea_version=0,
                content="test",
                query="test",
            )
    # PostgreSQL сериализует конкурирующие upsert, лимит общий для экземпляров сервиса.
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(lambda _: AuthService(service.sessions).rate_limit("concurrent", 5), range(20))
        )
    assert results.count(None) == 5
    service.disable_account("alice@example.test")
    assert alice.get(f"/test/conversations/{conversation_id}").status_code == 401
