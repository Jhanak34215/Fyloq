# ============================================================
# FYLOQ SUPABASE STORAGE
# File: storage.py
# ============================================================

import os

from dotenv import load_dotenv
from supabase import create_client, Client


# ============================================================
# ===== ENVIRONMENT START =====
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    ""
).strip()

SUPABASE_SECRET_KEY = os.getenv(
    "SUPABASE_SECRET_KEY",
    ""
).strip()

SUPABASE_STORAGE_BUCKET = os.getenv(
    "SUPABASE_STORAGE_BUCKET",
    "fyloq-files"
).strip()

# ============================================================
# ===== ENVIRONMENT END =====
# ============================================================


# ============================================================
# ===== CONFIGURATION VALIDATION START =====
# ============================================================

if not SUPABASE_URL:

    raise RuntimeError(
        "SUPABASE_URL is missing."
    )

if not SUPABASE_SECRET_KEY:

    raise RuntimeError(
        "SUPABASE_SECRET_KEY is missing."
    )

# ============================================================
# ===== CONFIGURATION VALIDATION END =====
# ============================================================


# ============================================================
# ===== SUPABASE CLIENT START =====
# ============================================================

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)

# ============================================================
# ===== SUPABASE CLIENT END =====
# ============================================================


# ============================================================
# ===== UPLOAD FILE START =====
# ============================================================

def upload_file_to_storage(
    stored_filename,
    file_data,
    content_type="application/octet-stream"
):

    return (
        supabase.storage
        .from_(
            SUPABASE_STORAGE_BUCKET
        )
        .upload(
            path=stored_filename,
            file=file_data,
            file_options={
                "content-type": content_type,
                "upsert": "false"
            }
        )
    )

# ============================================================
# ===== UPLOAD FILE END =====
# ============================================================


# ============================================================
# ===== DOWNLOAD FILE START =====
# ============================================================

def download_file_from_storage(
    stored_filename
):

    return (
        supabase.storage
        .from_(
            SUPABASE_STORAGE_BUCKET
        )
        .download(
            stored_filename
        )
    )

# ============================================================
# ===== DOWNLOAD FILE END =====
# ============================================================


# ============================================================
# ===== DELETE FILE START =====
# ============================================================

def delete_file_from_storage(
    stored_filename
):

    return (
        supabase.storage
        .from_(
            SUPABASE_STORAGE_BUCKET
        )
        .remove(
            [
                stored_filename
            ]
        )
    )

# ============================================================
# ===== DELETE FILE END =====
# ============================================================