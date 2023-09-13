import base64

from config import key, salt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


def generate_key(key: str, salt: str) -> bytes:
    kdf = Scrypt(salt=salt.encode(), length=32, n=2 ** 14, r=8, p=1)
    derived_key = kdf.derive(key.encode())
    return base64.urlsafe_b64encode(derived_key)


fernet = Fernet(generate_key(key, salt))
