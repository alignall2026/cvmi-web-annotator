import hashlib
import os
import shutil
from datetime import datetime
from cryptography.fernet import Fernet
from cvmi_analyzer.config import SECRET_KEY, BACKUP_DIR, DB_PATH

# 1. Column-Level Encryption for Patient Personal Data (PHI)
_cipher = Fernet(SECRET_KEY)

def encrypt_data(plain_text: str) -> str:
    """Encrypts clear text using the secret Fernet key."""
    if not plain_text:
        return ""
    return _cipher.encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt_data(cipher_text: str) -> str:
    """Decrypts Fernet encrypted cipher text back to clear text."""
    if not cipher_text:
        return ""
    try:
        return _cipher.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except Exception:
        # Returns raw if decryption fails (e.g. if database is corrupted or key mismatch)
        return "[Decryption Failed]"

# 2. Secure Password Hashing (PBKDF2-HMAC)
def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with a unique salt.
    Returns (hex_hash, hex_salt).
    """
    if salt is None:
        salt = os.urandom(16)
    
    # 100,000 iterations is a secure default
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return pwd_hash.hex(), salt.hex()

def verify_password(password: str, stored_hash: str, stored_salt_hex: str) -> bool:
    """Verifies a password against a stored PBKDF2 hash and salt."""
    try:
        salt = bytes.fromhex(stored_salt_hex)
        check_hash, _ = hash_password(password, salt)
        return check_hash == stored_hash
    except Exception:
        return False

# 3. Database Backup Management
def create_backup() -> str:
    """
    Creates an encrypted-ready file backup of the SQLite database.
    Returns the backup file path.
    """
    if not os.path.exists(DB_PATH):
        return ""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"cvmi_backup_{timestamp}.db"
    
    try:
        shutil.copy2(DB_PATH, backup_file)
        return str(backup_file)
    except Exception as e:
        print(f"Error creating database backup: {e}")
        return ""

def restore_backup(backup_file_path: str) -> bool:
    """Restores the database from a backup file."""
    if not os.path.exists(backup_file_path):
        return False
    try:
        # Backup the current database first in case restore fails
        if os.path.exists(DB_PATH):
            temp_backup = DB_PATH.with_suffix(".db.tmp")
            shutil.copy2(DB_PATH, temp_backup)
        
        shutil.copy2(backup_file_path, DB_PATH)
        
        # Clean up temp
        if os.path.exists(DB_PATH.with_suffix(".db.tmp")):
            os.remove(DB_PATH.with_suffix(".db.tmp"))
        return True
    except Exception as e:
        print(f"Error restoring database backup: {e}")
        # Rollback temp if possible
        if os.path.exists(DB_PATH.with_suffix(".db.tmp")):
            shutil.copy2(DB_PATH.with_suffix(".db.tmp"), DB_PATH)
            os.remove(DB_PATH.with_suffix(".db.tmp"))
        return False
