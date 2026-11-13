"""Database migrations and support account provisioning."""

import argparse
import getpass
from pathlib import Path

from . import main
from .auth import password_hash
from .legacy_schema import validate_legacy


def migrate():
    with main.connect_db() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(70419421)")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        paths = sorted(
            (Path(__file__).resolve().parents[1] / "migrations").glob("*.sql")
        )
        for path in paths:
            if connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version=%s", (path.name,)
            ).fetchone():
                continue
            exists = path.name[:3] in {"001", "002", "003"} and validate_legacy(
                connection, paths, path
            )
            if not exists:
                statement = (
                    path.read_text().replace("BEGIN;", "").replace("COMMIT;", "")
                )
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations(version) VALUES (%s)", (path.name,)
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "create-support"])
    parser.add_argument("--email")
    args = parser.parse_args()
    if args.command == "migrate":
        migrate()
    else:
        email = (args.email or input("Email: ")).strip().lower()
        password = getpass.getpass("Parolă (minimum 10 caractere): ")
        if "@" not in email or len(password) < 10:
            parser.error("Email sau parolă invalidă")
        with main.connect_db() as connection:
            connection.execute(
                "INSERT INTO users(email,password_hash,role) VALUES (%s,%s,'support')",
                (email, password_hash(password)),
            )
        print("Cont support creat.")
