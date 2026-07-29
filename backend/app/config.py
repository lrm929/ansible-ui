import os

# 项目根目录: backend/ 的上一级
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
TMP_DIR = os.path.join(DATA_DIR, "tmp")
REPOS_DIR = os.path.join(DATA_DIR, "repos")

DATABASE_URL = "sqlite:///" + os.path.join(DATA_DIR, "app.db").replace("\\", "/")

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

for d in (DATA_DIR, TMP_DIR, REPOS_DIR):
    os.makedirs(d, exist_ok=True)


def _load_or_create_key(path, generator):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    value = generator()
    with open(path, "w", encoding="utf-8") as f:
        f.write(value)
    return value


def _gen_jwt_secret():
    import secrets

    return secrets.token_hex(32)


def _gen_fernet_key():
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode("ascii")


JWT_SECRET = _load_or_create_key(os.path.join(DATA_DIR, "secret_key"), _gen_jwt_secret)
FERNET_KEY = _load_or_create_key(os.path.join(DATA_DIR, "fernet_key"), _gen_fernet_key)

FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
