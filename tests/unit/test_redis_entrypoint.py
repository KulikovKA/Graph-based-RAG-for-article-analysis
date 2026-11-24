"""Проверка конфигурации Redis на синтетических значениях без запуска службы."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "docker" / "redis-entrypoint.sh"
SHELL = shutil.which("sh") or r"C:\Program Files\Git\bin\bash.exe"


def test_redis_config_escapes_password(tmp_path):
    if not Path(SHELL).exists():
        pytest.skip("Нет POSIX shell")
    fake = tmp_path / "docker-entrypoint.sh"
    fake.write_text(
        "#!/bin/sh\n[ \"$1\" = redis-server ] && [ \"$2\" = - ] || exit 2\ncat\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PATH"] = str(tmp_path) + os.pathsep + env.get("PATH", "")
    env["REDIS_PASSWORD"] = 'synthetic"\\value'
    result = subprocess.run([SHELL, str(SCRIPT)], env=env, capture_output=True, text=True)
    assert result.returncode == 0
    assert 'requirepass "synthetic\\"\\\\value"' in result.stdout
    assert "appendonly yes" in result.stdout
    assert "maxmemory 256mb" in result.stdout
    assert "maxmemory-policy allkeys-lru" in result.stdout


def test_redis_rejects_control_chars():
    if not Path(SHELL).exists():
        pytest.skip("Нет POSIX shell")
    env = os.environ.copy()
    env["REDIS_PASSWORD"] = "synthetic\nvalue"
    result = subprocess.run([SHELL, str(SCRIPT)], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert "synthetic" not in result.stdout + result.stderr
