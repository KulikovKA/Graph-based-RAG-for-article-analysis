from fastapi.testclient import TestClient

from app.api.redaction import redact
from app.domain.contracts import AnswerV1, EvidenceV1, RunV1
from app.main import create_app


def test_fastapi_app_imports_and_health_contracts() -> None:
    client = TestClient(create_app())
    live = client.get("/health/live")
    ready = client.get("/health/ready")
    assert live.status_code == 200 and live.json() == {"status": "live"}
    assert ready.status_code == 503
    assert ready.json() == {"status": "not_ready", "reason": "dependencies_not_configured"}


def test_shared_contracts_import() -> None:
    assert AnswerV1 and RunV1 and EvidenceV1


def test_redaction_hides_secrets_and_credentials() -> None:
    assert redact({"api_key": "abc", "message": "Bearer secret"}) == {
        "api_key": "[REDACTED]", "message": "Bearer [REDACTED]"
    }
