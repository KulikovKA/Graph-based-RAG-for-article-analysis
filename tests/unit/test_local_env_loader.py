"""Компонентные проверки явной загрузки локального окружения."""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_with_env.py"


def run_loader(tmp_path, monkeypatch, first, second, *options):
    for name in ("TEST_LOCAL_ONE", "TEST_LOCAL_TWO"):
        monkeypatch.delenv(name, raising=False)
    one, two = tmp_path / "one", tmp_path / "two"
    one.write_text(first, encoding="utf-8")
    two.write_text(second, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(one), "--file", str(two), *options],
        capture_output=True, text=True, check=False,
    )


def test_selected_names_only(tmp_path, monkeypatch):
    result = run_loader(
        tmp_path, monkeypatch, "TEST_LOCAL_ONE=synthetic\n", "TEST_LOCAL_TWO=private\n",
        "--allow", "TEST_LOCAL_ONE", "--", sys.executable, "-c",
        "import os; assert os.environ['TEST_LOCAL_ONE']=='synthetic'; "
        "assert 'TEST_LOCAL_TWO' not in os.environ",
    )
    assert result.returncode == 0
    assert "private" not in result.stdout + result.stderr


def test_duplicate_and_invalid_values_fail_without_disclosure(tmp_path, monkeypatch):
    for first, second in [("TEST_LOCAL_ONE=synthetic\n", "TEST_LOCAL_ONE=private\n"),
                          ("TEST_LOCAL_ONE=$private\n", "")]:
        result = run_loader(tmp_path, monkeypatch, first, second, "--allow", "TEST_LOCAL_ONE",
                            "--", sys.executable, "-c", "raise SystemExit(99)")
        assert result.returncode == 2
        assert "private" not in result.stdout + result.stderr


def test_process_conflict_fails(tmp_path, monkeypatch):
    path = tmp_path / "env"
    path.write_text("TEST_LOCAL_ONE=synthetic\n", encoding="utf-8")
    env = os.environ.copy()
    env["TEST_LOCAL_ONE"] = "private"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(path), "--allow", "TEST_LOCAL_ONE",
         "--", sys.executable, "-c", "raise SystemExit(99)"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "private" not in result.stdout + result.stderr


def test_names_are_case_insensitive(tmp_path, monkeypatch):
    result = run_loader(
        tmp_path, monkeypatch, "test_local_one=synthetic\n", "TEST_LOCAL_ONE=private\n",
        "--allow", "TEST_LOCAL_ONE", "--", sys.executable, "-c", "raise SystemExit(99)",
    )
    assert result.returncode == 2
    assert "private" not in result.stdout + result.stderr

    path = tmp_path / "env"
    path.write_text("test_local_one=synthetic\n", encoding="utf-8")
    env = os.environ.copy()
    env["TeSt_LoCaL_OnE"] = "private"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(path), "--allow", "TEST_LOCAL_ONE",
         "--", sys.executable, "-c", "raise SystemExit(99)"],
        env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "private" not in result.stdout + result.stderr
