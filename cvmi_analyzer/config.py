import os
from pathlib import Path

# Application Names
APP_NAME = "CVMI Analyzer Pro"
ORG_NAME = "Orthodontic Research Lab"

# Directory Structure Setup
# We use standard user directory for local persistence of database, models, and backups
USER_HOME = Path(os.path.expanduser("~"))
APP_DATA_DIR = USER_HOME / ".cvmi_analyzer"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DATA_DIR / "cvmi_database.db"
BACKUP_DIR = APP_DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

MODEL_DIR = APP_DATA_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_MODEL_PATH = MODEL_DIR / "cvmi_model.pth"
ONNX_MODEL_PATH = MODEL_DIR / "cvmi_model.onnx"

# Default Encryption Key & Admin Credentials (In production, keys would be generated on installation)
# For the local demonstration, we provide a secure fallback or generate one locally
SECRET_KEY_PATH = APP_DATA_DIR / ".secret.key"
if not SECRET_KEY_PATH.exists():
    from cryptography.fernet import Fernet
    SECRET_KEY_PATH.write_bytes(Fernet.generate_key())

SECRET_KEY = SECRET_KEY_PATH.read_bytes()

DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin123"

# Image File Formats Supported
SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".dcm"]

# CVMI Analysis Parameters
# Scale defaults: 1.0 means 1 pixel = 1 pixel. If calibrated, it is pixels per mm.
DEFAULT_CALIBRATION_SCALE = 1.0  # pixels/mm

# Vertebrae Landmark Labels
LANDMARK_LABELS = {
    "C2": ["SA", "SP", "IA", "IP", "IM"],
    "C3": ["SA", "SP", "IA", "IP", "IM"],
    "C4": ["SA", "SP", "IA", "IP", "IM"]
}

# Descriptions of CS Stages for UI reference
STAGE_DESCRIPTIONS = {
    "CS1": "Inferior borders of C2, C3, and C4 are flat. Vertebral bodies of C3 and C4 are wedge-shaped.",
    "CS2": "Concavity present at C2 inferior border. C3 and C4 are rectangular horizontal.",
    "CS3": "Concavity present at C2 and C3 inferior borders. C3 and C4 are rectangular horizontal.",
    "CS4": "Concavity present at C2, C3, and C4 inferior borders. C3 and C4 are rectangular horizontal.",
    "CS5": "Concavity present at C2, C3, and C4 inferior borders. C3 and C4 are square-shaped.",
    "CS6": "Concavity present at C2, C3, and C4 inferior borders. C3 and C4 are rectangular vertical."
}
