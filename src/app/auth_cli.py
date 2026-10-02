"""Операторская CLI без паролей в argv и публичной регистрации."""

import argparse
import getpass
import os

from sqlalchemy.exc import IntegrityError

from app.services.auth import AuthService
from app.storage.repositories import make_engine, make_session_factory


def main() -> None:
    parser = argparse.ArgumentParser(description="Локальные аккаунты")
    parser.add_argument("action", choices=["create", "disable"])
    parser.add_argument("email")
    args = parser.parse_args()
    url = os.getenv("DATABASE_URL")
    if not url:
        parser.exit(1, "DATABASE_URL не задан\n")
    engine = make_engine(url)
    service = AuthService(make_session_factory(engine))
    try:
        if args.action == "create":
            password = getpass.getpass("Пароль: ")
            if password != getpass.getpass("Повторите пароль: "):
                raise ValueError("Пароли не совпадают")
            user_id = service.create_account(args.email, password)
            print(f"Аккаунт создан: {user_id}")
        else:
            service.disable_account(args.email)
            print("Аккаунт отключён, сессии отозваны")
    except IntegrityError:
        parser.exit(1, "Аккаунт уже существует\n")
    except (ValueError, LookupError) as exc:
        parser.exit(1, f"{exc}\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
