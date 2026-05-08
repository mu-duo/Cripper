import os
from pathlib import Path
from cryptography.fernet import Fernet

CONFIG_PATH = Path.home() / ".cripper"
IGNORE_FILE = ".cripperignore"
DEFAULT_ENCRYPTION_FILE = "default.enc"


def get_or_create_key():
    if CONFIG_PATH.exists():
        return CONFIG_PATH.read_text().strip()

    key = Fernet.generate_key().decode()
    CONFIG_PATH.write_text(key)
    if os.name != "nt":
        CONFIG_PATH.chmod(0o600)
    return key
