"""Sets the site password. Only an Argon2id hash of it is saved, in .env.

Run from the repo root: python -m scripts.set_password
"""
import getpass
import secrets
from pathlib import Path

from dotenv import dotenv_values, set_key

from app.auth import hash_password

ENV_PATH = Path(__file__).parent.parent / ".env"
MIN_LENGTH = 14


def main():
    password = getpass.getpass("New site password: ")
    if len(password) < MIN_LENGTH:
        raise SystemExit(f"Use at least {MIN_LENGTH} characters.")
    if password != getpass.getpass("Type it again: "):
        raise SystemExit("Those didn't match.")

    ENV_PATH.touch()
    set_key(ENV_PATH, "APP_PASSWORD_HASH", hash_password(password))
    if not dotenv_values(ENV_PATH).get("SESSION_SECRET"):
        set_key(ENV_PATH, "SESSION_SECRET", secrets.token_urlsafe(48))
    print("Password saved. Restart the server, and everyone will need to log in again.")


if __name__ == "__main__":
    main()
