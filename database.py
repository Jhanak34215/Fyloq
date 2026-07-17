# ============================================================
# QUICKVAULT DATABASE CONFIGURATION
# File: database.py
# ============================================================
import os
from dotenv import load_dotenv


from sqlalchemy import create_engine,text
from sqlalchemy.engine import Engine
load_dotenv()

# ============================================================
# ===== DATABASE URL START =====
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

LOCAL_DATABASE_PATH = os.path.join(
    BASE_DIR,
    "instance",
    "quickvault.db"
)

DEFAULT_DATABASE_URL = (
    "sqlite:///"
    +
    LOCAL_DATABASE_PATH.replace(
        "\\",
        "/"
    )
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    DEFAULT_DATABASE_URL
)

# ============================================================
# ===== DATABASE URL END =====
# ============================================================


# ============================================================
# ===== RENDER POSTGRES URL FIX START =====
# ============================================================

if DATABASE_URL.startswith(
    "postgres://"
):

    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg://",
        1
    )

elif DATABASE_URL.startswith(
    "postgresql://"
):

    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )

# ============================================================
# ===== RENDER POSTGRES URL FIX END =====
# ============================================================


# ============================================================
# ===== DATABASE ENGINE START =====
# ============================================================

engine_options = {
    "pool_pre_ping": True
}

if DATABASE_URL.startswith(
    "sqlite"
):

    engine_options[
        "connect_args"
    ] = {
        "check_same_thread": False
    }

database_engine: Engine = create_engine(
    DATABASE_URL,
    **engine_options
)

# ============================================================
# ===== DATABASE ENGINE END =====
# ============================================================


# ============================================================
# ===== DATABASE CONNECTION HELPER START =====
# ============================================================

def get_database_engine() -> Engine:

    return database_engine

# ============================================================
# ===== DATABASE CONNECTION HELPER END =====
# ============================================================