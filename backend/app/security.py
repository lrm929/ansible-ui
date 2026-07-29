import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
from cryptography.fernet import Fernet

from .config import FERNET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS, JWT_SECRET

_PBKDF2_ITERATIONS = 100_000

_fernet = Fernet(FERNET_KEY.encode("ascii"))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(_PBKDF2_ITERATIONS, salt.hex(), dk.hex())


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def encrypt_secret(plain: str) -> str:
    return _fernet.encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode("ascii")).decode("utf-8")
