import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from itsdangerous import BadSignature, URLSafeTimedSerializer

SESSION_SECONDS = 12 * 60 * 60

hasher = PasswordHasher()  # Argon2id with the library's RFC 9106 defaults


def hash_password(password):
    return hasher.hash(password)


def password_matches(password, password_hash):
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


class Sessions:
    """Signed, expiring session tokens. Changing the password logs everyone out."""

    def __init__(self, secret, password_hash):
        salt = hashlib.sha256(password_hash.encode()).hexdigest()
        self.serializer = URLSafeTimedSerializer(secret, salt=salt)

    def create(self):
        return self.serializer.dumps({"sid": secrets.token_urlsafe(16)})

    def read(self, token):
        """Returns the session id, or None if the token is missing, forged or expired."""
        if not token:
            return None
        try:
            return self.serializer.loads(token, max_age=SESSION_SECONDS)["sid"]
        except BadSignature:
            return None
