import os

# Konfigurasi aplikasi SalSa Market Intelligence System
SECRET_KEY = os.getenv("SECRET_KEY", "salsa-market-secret-key-2024-ganti-di-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", 8))

# Path database SQLite
DATABASE_URL = "sqlite:///./salsa_market.db"

# Path folder model terlatih
TRAINED_MODELS_DIR = "trained_models"

# Akun default peneliti saat seed pertama kali
DEFAULT_PENELITI_USERNAME = "admin"
DEFAULT_PENELITI_PASSWORD = "admin123"
DEFAULT_PENELITI_NAMA = "Administrator Peneliti"
