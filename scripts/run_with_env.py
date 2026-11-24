"""Явно передать выбранные переменные дочернему локальному процессу."""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or not NAME.fullmatch(name) or name.upper() in values:
            raise ValueError(f"Некорректная или повторная запись: {path.name}:{number}")
        # Поддерживается только буквальное значение: без раскрытия переменных и кавычек.
        if any(char in value for char in "'\"$\\") or " #" in value:
            raise ValueError(f"Недопустимый формат: {path.name}:{number}")
        values[name.upper()] = value
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", action="append", required=True, type=Path)
    parser.add_argument("--allow", action="append", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Укажите команду после --")
    try:
        values: dict[str, str] = {}
        for path in args.file:
            current = read_env(path)
            if values.keys() & current.keys():
                raise ValueError("Повторные имена в env-файлах")
            values.update(current)
        allowed = {name.upper() for name in args.allow}
        if any(not NAME.fullmatch(name) for name in allowed) or allowed - values.keys():
            raise ValueError("Неизвестное или недопустимое имя в --allow")
        process_names = {name.upper() for name in os.environ}
        conflicts = sorted(name for name in allowed if name in process_names)
        if conflicts:
            raise ValueError("Переменные уже присутствуют в процессе: " + ", ".join(conflicts))
        child_env = os.environ.copy()
        # Не передавать остальные значения из файлов дочернему процессу.
        child_env.update({name: values[name] for name in allowed})
        return subprocess.call(command, env=child_env)
    except (OSError, ValueError) as exc:
        print(f"Ошибка загрузки окружения: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
