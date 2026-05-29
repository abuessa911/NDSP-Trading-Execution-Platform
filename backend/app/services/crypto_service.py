from cryptography.fernet import Fernet
from app.core.config import settings


def _fernet() -> Fernet:
    return Fernet(settings.FERNET_KEY.encode())


def encrypt_text(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_text(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
