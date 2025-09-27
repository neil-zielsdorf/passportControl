import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class DocumentEncryption:
    def __init__(self, password: str = None):
        if password is None:
            password = os.getenv('ENCRYPTION_KEY', 'default-passport-manager-key-change-this')

        self.key = self._derive_key(password.encode())
        self.cipher = Fernet(self.key)

    def _derive_key(self, password: bytes) -> bytes:
        salt = b'passport_manager_salt'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key

    def encrypt(self, text: str) -> str:
        if not text:
            return ""
        encrypted_bytes = self.cipher.encrypt(text.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()

    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text:
            return ""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception:
            return encrypted_text

_encryption_instance = None

def get_encryption():
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = DocumentEncryption()
    return _encryption_instance