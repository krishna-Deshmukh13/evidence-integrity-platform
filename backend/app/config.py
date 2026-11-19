"""Settings read from environment / backend/.env (no extra dependency)."""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file():
    f = BASE_DIR / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env_file()

STORAGE_DIR = Path(os.environ.get("EI_STORAGE_DIR", BASE_DIR / "storage"))
UPLOAD_DIR = STORAGE_DIR / "uploads"
ARTIFACT_DIR = STORAGE_DIR / "artifacts"
for d in (UPLOAD_DIR, ARTIFACT_DIR):
    d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{(STORAGE_DIR / 'evidence.db').as_posix()}")

_secret_file = STORAGE_DIR / ".jwt_secret"
JWT_SECRET = os.environ.get("JWT_SECRET") or ""
if not JWT_SECRET:
    if _secret_file.exists():
        JWT_SECRET = _secret_file.read_text().strip()
    else:
        JWT_SECRET = secrets.token_hex(32)
        try:
            _secret_file.write_text(JWT_SECRET)
        except OSError:
            pass

ACCESS_TOKEN_MINUTES = int(os.environ.get("ACCESS_TOKEN_MINUTES", "15"))
REFRESH_TOKEN_DAYS = int(os.environ.get("REFRESH_TOKEN_DAYS", "7"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
SYNC_ANALYSIS = os.environ.get("EI_SYNC", "0") == "1"  # tests: analyse inline
LOGIN_MAX_FAILS = 5
LOGIN_BLOCK_SECONDS = 15 * 60

MEDIA_TYPES = {
    "image": {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "gif"},
    "video": {"mp4", "mov", "avi", "mkv", "webm", "3gp", "wmv"},
    "audio": {"mp3", "wav", "m4a", "aac", "ogg", "opus", "flac", "amr", "wma"},
    "document": {"pdf", "docx"},
}
