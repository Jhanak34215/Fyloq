# ============================================================
# FYLOQ BACKEND
# File: app.py
# ============================================================


# ===== 01. IMPORTS START =====

import base64
import hmac
import os
import secrets
import sqlite3
import time
import uuid
import zipfile

from datetime import datetime, timedelta
from io import BytesIO

import qrcode
from flask_wtf.csrf import (
    CSRFError,
    CSRFProtect
)
from dotenv import load_dotenv
from database import (
    get_database_connection,
    is_sqlite_database
)
from storage import (
    upload_file_to_storage,
    download_file_from_storage,
    delete_file_from_storage
)
from file_encryption import (
    encrypt_file_data,
    decrypt_file_data
)
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for
)
from flask_limiter import Limiter

from flask_limiter.util import get_remote_address
from itsdangerous import (
    BadSignature,
    SignatureExpired,
    URLSafeTimedSerializer
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from werkzeug.utils import secure_filename

# ===== 01. IMPORTS END =====


# ===== 02. ENVIRONMENT VARIABLES START =====

load_dotenv()

# ============================================================
# ===== ADMIN CREDENTIAL ENVIRONMENT START =====
# ============================================================

ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME",
    ""
).strip()

ADMIN_PASSWORD = os.getenv(
    "ADMIN_PASSWORD",
    ""
)

ADMIN_PASSWORD_HASH = os.getenv(
    "ADMIN_PASSWORD_HASH",
    ""
).strip()

# ============================================================
# ===== ADMIN CREDENTIAL ENVIRONMENT END =====
# ============================================================

# ============================================================
# ===== APPLICATION ENVIRONMENT START =====
# ============================================================

APP_ENV = os.getenv(
    "APP_ENV",
    "development"
).strip().lower()

IS_PRODUCTION = (
    APP_ENV == "production"
)

# ============================================================
# ===== APPLICATION ENVIRONMENT END =====
# ============================================================
# ===== 02. ENVIRONMENT VARIABLES END =====


# ===== 03. FLASK APP CONFIGURATION START =====

app = Flask(__name__)


# ============================================================
# ===== RATE LIMITER START =====
# ============================================================

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[]
)

# ============================================================
# ===== RATE LIMITER END =====
# ============================================================

# ============================================================
# ===== SECURE FLASK SECRET KEY START =====
# ============================================================

FLASK_SECRET_KEY = os.getenv(
    "FLASK_SECRET_KEY",
    ""
).strip()

if IS_PRODUCTION and not FLASK_SECRET_KEY:

    raise RuntimeError(
        "FLASK_SECRET_KEY is required in production."
    )

if not FLASK_SECRET_KEY:

    FLASK_SECRET_KEY = secrets.token_hex(
        32
    )

app.config["SECRET_KEY"] = FLASK_SECRET_KEY

# ============================================================
# ===== SECURE FLASK SECRET KEY END =====
# ============================================================

# ============================================================
# ===== CSRF PROTECTION START =====
# ============================================================

csrf = CSRFProtect(
    app
)

# ============================================================
# ===== CSRF PROTECTION END =====
# ============================================================
# ============================================================
# ===== ADMIN SESSION SECURITY START =====
# ============================================================

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    minutes=30
)

app.config["SESSION_COOKIE_HTTPONLY"] = True

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Local development me False rahega.
# Deployment ke waqt HTTPS par True karenge.
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION

# Fyloq ke liye alag session-cookie name.
app.config["SESSION_COOKIE_NAME"] = (
    "fyloq_session"
)

# Har authenticated request par permanent session refresh hogi.
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

# Current Flask-WTF compatibility ke liye seconds use kiye hain.
# 7200 seconds = 2 hours.
app.config["WTF_CSRF_TIME_LIMIT"] = 7200

# Production HTTPS par strict CSRF referrer checking.
app.config["WTF_CSRF_SSL_STRICT"] = IS_PRODUCTION

app.config["PREFERRED_URL_SCHEME"] = (
    "https"
    if IS_PRODUCTION
    else "http"
)

# ============================================================
# ===== ADMIN SESSION SECURITY END =====
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "instance",
    "quickvault.db"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = (
    10 * 1024 * 1024
)

download_token_serializer = URLSafeTimedSerializer(
    app.config["SECRET_KEY"]
)

# ===== 03. FLASK APP CONFIGURATION END =====



# ============================================================
# ===== PRODUCTION CONFIGURATION VALIDATION START =====
# ============================================================

if IS_PRODUCTION:

    if not ADMIN_USERNAME:

        raise RuntimeError(
            "ADMIN_USERNAME is required in production."
        )

    if (
        not ADMIN_PASSWORD
        and
        not ADMIN_PASSWORD_HASH
    ):

        raise RuntimeError(
            "ADMIN_PASSWORD or ADMIN_PASSWORD_HASH "
            "is required in production."
        )

# ============================================================
# ===== PRODUCTION CONFIGURATION VALIDATION END =====
# ============================================================

# ===== 04. SECURITY SETTINGS START =====


# ============================================================
# ===== FILE PIN SECURITY SETTINGS START =====
# ============================================================

MAX_PIN_ATTEMPTS = 4

PIN_LOCK_MINUTES = 15
# ============================================================
# ===== WEAK FILE PIN LIST START =====
# ============================================================

WEAK_FILE_PINS = {

    "0000",
    "1111",
    "2222",
    "3333",
    "4444",
    "5555",
    "6666",
    "7777",
    "8888",
    "9999",
    "1234",
    "4321"

}

# ============================================================
# ===== WEAK FILE PIN LIST END =====
# ============================================================
# ============================================================
# ===== FYLOQ STORAGE LIMIT START =====
# ============================================================

FYLOQ_STORAGE_LIMIT = (
    850 * 1024 * 1024
)

# ============================================================
# ===== FYLOQ STORAGE LIMIT END =====
# ============================================================
# ============================================================
# ===== GDPR DATA RETENTION SETTINGS START =====
# ============================================================

SUPPORT_RETENTION_DAYS = int(
    os.getenv(
        "SUPPORT_RETENTION_DAYS",
        "180"
    )
)

ABUSE_RETENTION_DAYS = int(
    os.getenv(
        "ABUSE_RETENTION_DAYS",
        "365"
    )
)

PRIVACY_REQUEST_RETENTION_DAYS = int(
    os.getenv(
        "PRIVACY_REQUEST_RETENTION_DAYS",
        "730"
    )
)

AUDIT_LOG_RETENTION_DAYS = int(
    os.getenv(
        "AUDIT_LOG_RETENTION_DAYS",
        "730"
    )
)

# ============================================================
# ===== GDPR DATA RETENTION SETTINGS END =====
# ============================================================
# ============================================================
# ===== FILE PIN SECURITY SETTINGS END =====
# ============================================================

CLEANUP_INTERVAL_SECONDS = 60

last_cleanup_timestamp = 0

# ============================================================
# ===== ADMIN LOGIN SECURITY SETTINGS START =====
# ============================================================

MAX_ADMIN_LOGIN_ATTEMPTS = 5

ADMIN_LOGIN_LOCK_MINUTES = 10

admin_failed_login_attempts = 0

admin_login_locked_until = None

# ============================================================
# ===== ADMIN LOGIN SECURITY SETTINGS END =====
# ============================================================
# ===== 04. SECURITY SETTINGS END =====


# ===== 05. ALLOWED FILE TYPES START =====

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "jpg",
    "jpeg",
    "png",
    "zip"
}

# ===== 05. ALLOWED FILE TYPES END =====


# ===== 06. REQUIRED FOLDERS START =====

os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True
)

os.makedirs(
    os.path.dirname(DATABASE_PATH),
    exist_ok=True
)

# ===== 06. REQUIRED FOLDERS END =====




# ===== 08. DATABASE TABLE CREATION START =====

def create_database():

    connection = get_database_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS files (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            original_filename TEXT NOT NULL,

            stored_filename TEXT NOT NULL,

            access_code TEXT NOT NULL UNIQUE,

            pin_hash TEXT,

            file_size INTEGER NOT NULL,

            file_extension TEXT NOT NULL,

            expiry_minutes INTEGER NOT NULL,

            uploaded_at TEXT NOT NULL,

            expires_at TEXT NOT NULL,

            one_time_download INTEGER DEFAULT 0,

            download_count INTEGER DEFAULT 0,

            status TEXT DEFAULT 'active',

            failed_pin_attempts INTEGER DEFAULT 0,

            locked_until TEXT,

            transfer_mode TEXT DEFAULT 'download',

            view_count INTEGER DEFAULT 0,

            last_viewed_at TEXT,

            print_count INTEGER DEFAULT 0,

            last_printed_at TEXT

        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS report_abuse (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            full_name TEXT NOT NULL,

            email TEXT NOT NULL,

            access_code TEXT,

            complaint_type TEXT NOT NULL,

            subject TEXT NOT NULL,

            description TEXT NOT NULL,

            status TEXT DEFAULT 'Pending',

            created_at TEXT NOT NULL

        )
        """
    )

    connection.commit()

    connection.close()
# ===== 08. DATABASE TABLE CREATION END =====


# ===== 09. EXISTING DATABASE MIGRATION START =====

def migrate_database():

    connection = get_database_connection()

    columns = connection.execute(
        """
        PRAGMA table_info(files)
        """
    ).fetchall()

    existing_columns = {
        column["name"]
        for column in columns
    }

    if "failed_pin_attempts" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN failed_pin_attempts
            INTEGER DEFAULT 0
            """
        )

    if "locked_until" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN locked_until TEXT
            """
        )

    # ============================================================
    # ===== VIEW + PRINT DATABASE MIGRATION START =====
    # ============================================================

    if "transfer_mode" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN transfer_mode
            TEXT DEFAULT 'download'
            """
        )

    if "view_count" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN view_count
            INTEGER DEFAULT 0
            """
        )

    if "last_viewed_at" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN last_viewed_at TEXT
            """
        )

    if "print_count" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN print_count
            INTEGER DEFAULT 0
            """
        )

    if "last_printed_at" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN last_printed_at TEXT
            """
        )
    # ============================================================
    # ===== FILE ENCRYPTION DATABASE MIGRATION START =====
    # ============================================================

    if "encryption_algorithm" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN encryption_algorithm TEXT
            """
        )

    if "encryption_version" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN encryption_version INTEGER
            """
        )

    if "encryption_key_version" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN encryption_key_version INTEGER
            """
        )

    if "file_nonce" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN file_nonce TEXT
            """
        )

    if "wrapped_data_key" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN wrapped_data_key TEXT
            """
        )

    if "key_wrap_nonce" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN key_wrap_nonce TEXT
            """
        )

    if "encrypted_size" not in existing_columns:

        connection.execute(
            """
            ALTER TABLE files
            ADD COLUMN encrypted_size INTEGER
            """
        )

    # ============================================================
    # ===== FILE ENCRYPTION DATABASE MIGRATION END =====
    # ============================================================
    # Purani uploaded files automatically normal
    # download mode me rahengi.
    connection.execute(
        """
        UPDATE files
        SET transfer_mode = 'download'
        WHERE transfer_mode IS NULL
           OR transfer_mode = ''
        """
    )

    connection.execute(
        """
        UPDATE files
        SET view_count = 0
        WHERE view_count IS NULL
        """
    )

    connection.execute(
        """
        UPDATE files
        SET print_count = 0
        WHERE print_count IS NULL
        """
    )

    # ============================================================
    # ===== VIEW + PRINT DATABASE MIGRATION END =====
    # ============================================================

    connection.commit()

    connection.close()
# ===== 09. EXISTING DATABASE MIGRATION END =====


# ===== 10. FILE VALIDATION START =====

def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )
# ============================================================
# ===== REAL FILE SIGNATURE VALIDATION START =====
# ============================================================

OLE_SIGNATURE = bytes.fromhex(
    "D0CF11E0A1B11AE1"
)


def validate_uploaded_file_signature(
    uploaded_file,
    file_extension
):

    try:

        uploaded_file.stream.seek(0)

        file_data = uploaded_file.stream.read()

        uploaded_file.stream.seek(0)

        if not file_data:

            return False, "The selected file is empty."

        # ===== PDF VALIDATION =====

        if file_extension == "pdf":

            if not file_data.startswith(
                b"%PDF-"
            ):

                return (
                    False,
                    "The uploaded file is not a valid PDF."
                )

            return True, None


        # ===== PNG VALIDATION =====

        if file_extension == "png":

            png_signature = (
                b"\x89PNG\r\n\x1a\n"
            )

            if not file_data.startswith(
                png_signature
            ):

                return (
                    False,
                    "The uploaded file is not a valid PNG image."
                )

            return True, None


        # ===== JPEG VALIDATION =====

        if file_extension in {
            "jpg",
            "jpeg"
        }:

            if not file_data.startswith(
                b"\xff\xd8\xff"
            ):

                return (
                    False,
                    "The uploaded file is not a valid JPEG image."
                )

            return True, None


        # ===== TEXT VALIDATION =====

        if file_extension == "txt":

            sample = file_data[:8192]

            if b"\x00" in sample:

                return (
                    False,
                    "The uploaded file is not a valid text file."
                )

            try:

                sample.decode(
                    "utf-8"
                )

            except UnicodeDecodeError:

                try:

                    sample.decode(
                        "latin-1"
                    )

                except UnicodeDecodeError:

                    return (
                        False,
                        "The uploaded file is not a valid text file."
                    )

            return True, None


        # ===== LEGACY MICROSOFT OFFICE VALIDATION =====

        if file_extension in {
            "doc",
            "xls",
            "ppt"
        }:

            if not file_data.startswith(
                OLE_SIGNATURE
            ):

                return (
                    False,
                    "The uploaded Microsoft Office file is invalid."
                )

            return True, None


        # ===== ZIP-BASED FILE VALIDATION =====

        if file_extension in {
            "zip",
            "docx",
            "xlsx",
            "pptx"
        }:

            if not file_data.startswith(
                b"PK"
            ):

                return (
                    False,
                    "The uploaded ZIP or Office file is invalid."
                )

            try:

                with zipfile.ZipFile(
                    BytesIO(file_data)
                ) as zip_file:

                    zip_members = set(
                        zip_file.namelist()
                    )

                    bad_member = zip_file.testzip()

                    if bad_member is not None:

                        return (
                            False,
                            "The uploaded archive is corrupted."
                        )

                    if file_extension == "docx":

                        if not any(
                            member.startswith(
                                "word/"
                            )
                            for member in zip_members
                        ):

                            return (
                                False,
                                "The uploaded file is not a valid DOCX document."
                            )

                    elif file_extension == "xlsx":

                        if not any(
                            member.startswith(
                                "xl/"
                            )
                            for member in zip_members
                        ):

                            return (
                                False,
                                "The uploaded file is not a valid XLSX spreadsheet."
                            )

                    elif file_extension == "pptx":

                        if not any(
                            member.startswith(
                                "ppt/"
                            )
                            for member in zip_members
                        ):

                            return (
                                False,
                                "The uploaded file is not a valid PPTX presentation."
                            )

            except (
                zipfile.BadZipFile,
                RuntimeError,
                ValueError
            ):

                return (
                    False,
                    "The uploaded archive or Office file is invalid."
                )

            return True, None


        return (
            False,
            "This file type is not supported."
        )

    except (
        OSError,
        AttributeError,
        ValueError
    ):

        uploaded_file.stream.seek(0)

        return (
            False,
            "The file could not be securely validated."
        )


# ============================================================
# ===== REAL FILE SIGNATURE VALIDATION END =====
# ============================================================

# ===== 10. FILE VALIDATION END =====


# ===== 11. FILE SIZE FORMATTER START =====

def format_size(size):

    if size >= 1024 * 1024 * 1024:

        return (
            f"{size / (1024 * 1024 * 1024):.2f} GB"
        )

    if size >= 1024 * 1024:

        return (
            f"{size / (1024 * 1024):.2f} MB"
        )

    if size >= 1024:

        return (
            f"{size / 1024:.2f} KB"
        )

    return f"{size} Bytes"

# ===== 11. FILE SIZE FORMATTER END =====


# ===== 12. ACCESS CODE GENERATOR START =====

def generate_access_code():

    connection = get_database_connection()

    while True:

        # Cryptographically secure 6-digit access code.
        access_code = str(
            100000
            +
            secrets.randbelow(
                900000
            )
        )

        existing_file = connection.execute(
            """
            SELECT id
            FROM files
            WHERE access_code = ?
            """,
            (access_code,)
        ).fetchone()

        if existing_file is None:

            connection.close()

            return access_code

# ===== 12. ACCESS CODE GENERATOR END =====


# ===== 13. DELETE STORED FILE HELPER START =====

def delete_stored_file(stored_filename):

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        stored_filename
    )

    if os.path.exists(file_path):

        os.remove(file_path)

# ===== 13. DELETE STORED FILE HELPER END =====


# ===== 14. FILE EXPIRY CHECK START =====

def is_file_expired(file_record):

    expires_at = datetime.fromisoformat(
        file_record["expires_at"]
    )

    return datetime.now() >= expires_at

# ===== 14. FILE EXPIRY CHECK END =====


# ===== 15. MARK FILE EXPIRED START =====

def mark_file_expired(file_record):

    # ============================================================
    # ===== SUPABASE STORAGE DELETE START =====
    # ============================================================

    try:

        delete_file_from_storage(
            file_record["stored_filename"]
        )

    except Exception as error:

        error_text = str(
            error
        ).lower()

        # Storage me file already missing ho,
        # to DB cleanup continue kar sakte hain.
        if not (
            "404" in error_text
            or
            "not found" in error_text
        ):

            print(
                "Expired file Storage delete failed:",
                error
            )

            # Storage delete fail hua to DB record preserve karo,
            # taaki cleanup baad me retry kar sake.
            return False

    # ============================================================
    # ===== SUPABASE STORAGE DELETE END =====
    # ============================================================


    # ============================================================
    # ===== DATABASE RECORD DELETE START =====
    # ============================================================

    connection = get_database_connection()

    try:

        connection.execute(
            """
            DELETE FROM files
            WHERE id = ?
            """,
            (
                file_record["id"],
            )
        )

        connection.commit()

    except Exception as error:

        try:

            connection.rollback()

        except Exception:

            pass

        print(
            "Expired file database cleanup failed:",
            error
        )

        return False

    finally:

        connection.close()

    # ============================================================
    # ===== DATABASE RECORD DELETE END =====
    # ============================================================

    return True

# ===== 15. MARK FILE EXPIRED END =====


# ===== 16. MARK FILE MISSING START =====

def mark_file_missing(file_id):

    connection = get_database_connection()

    connection.execute(
        """
        UPDATE files
        SET status = 'missing'
        WHERE id = ?
        """,
        (file_id,)
    )

    connection.commit()

    connection.close()

# ===== 16. MARK FILE MISSING END =====


# ===== 17. AUTOMATIC EXPIRED FILE CLEANUP START =====

def cleanup_expired_files():

    connection = get_database_connection()

    deleted_count = 0

    try:

        active_files = connection.execute(
            """
            SELECT *
            FROM files
            WHERE status = 'active'
            """
        ).fetchall()

        for file_record in active_files:

            if not is_file_expired(
                file_record
            ):

                continue

            storage_deleted = False

            try:

                delete_file_from_storage(
                    file_record["stored_filename"]
                )

                storage_deleted = True

            except Exception as error:

                error_text = str(
                    error
                ).lower()

                # File Storage me already missing hai,
                # to expired DB record safely remove kar sakte hain.
                if (
                    "404" in error_text
                    or
                    "not found" in error_text
                ):

                    storage_deleted = True

                else:

                    print(
                        "Expired file Storage cleanup failed:",
                        file_record["stored_filename"],
                        error
                    )

            # Storage delete fail hua to DB record preserve karo.
            if not storage_deleted:

                continue

            connection.execute(
                """
                DELETE FROM files
                WHERE id = ?
                """,
                (
                    file_record["id"],
                )
            )

            deleted_count += 1

        connection.commit()

    except Exception as error:

        try:

            connection.rollback()

        except Exception:

            pass

        print(
            "Automatic expired file cleanup failed:",
            error
        )

    finally:

        connection.close()

    return deleted_count

# ===== 17. AUTOMATIC EXPIRED FILE CLEANUP END =====

# ============================================================
# ===== PERMANENT EXPIRED RECORD CLEANUP START =====
# ============================================================

def permanently_delete_expired_files():

    connection = get_database_connection()

    deleted_count = 0
    deleted_storage = 0

    try:

        expired_records = connection.execute(
            """
            SELECT *
            FROM files
            WHERE status = 'expired'
            """
        ).fetchall()

        for file_record in expired_records:

            storage_deleted = False

            try:

                delete_file_from_storage(
                    file_record["stored_filename"]
                )

                storage_deleted = True

            except Exception as error:

                error_text = str(
                    error
                ).lower()

                # Storage me file already missing ho
                # to DB record safely remove kar sakte hain.
                if (
                    "404" in error_text
                    or
                    "not found" in error_text
                ):

                    storage_deleted = True

                else:

                    print(
                        "Permanent Storage cleanup failed:",
                        file_record["stored_filename"],
                        error
                    )


            # Storage deletion fail hui to
            # DB record preserve karo.
            if not storage_deleted:

                continue


            connection.execute(
                """
                DELETE FROM files
                WHERE id = ?
                """,
                (
                    file_record["id"],
                )
            )

            deleted_count += 1

            deleted_storage += (
                file_record["file_size"]
                or 0
            )


        connection.commit()


    except Exception as error:

        try:

            connection.rollback()

        except Exception:

            pass

        print(
            "Permanent expired cleanup failed:",
            error
        )


    finally:

        connection.close()


    return {
        "deleted_count": deleted_count,
        "deleted_storage": deleted_storage
    }

# ============================================================
# ===== PERMANENT EXPIRED RECORD CLEANUP END =====
# ============================================================

# ============================================================
# ===== GDPR PERSONAL DATA RETENTION CLEANUP START =====
# ============================================================

def cleanup_expired_personal_data():

    current_time = datetime.now().isoformat()

    connection = None

    cleanup_counts = {
        "support_anonymized": 0,
        "abuse_anonymized": 0,
        "privacy_anonymized": 0,
        "audit_deleted": 0
    }

    try:

        connection = get_database_connection()


        # ====================================================
        # ===== SUPPORT REQUEST ANONYMIZATION START =====
        # ====================================================

        support_cursor = connection.execute(
            """
            UPDATE support_requests

            SET
                name = 'Anonymized User',
                email = 'anonymized@invalid.local',
                access_code = NULL,
                subject = 'Anonymized support request',
                message = 'Personal data removed after retention period.',
                anonymized_at = ?

            WHERE
                retention_until IS NOT NULL
                AND retention_until <= ?
                AND anonymized_at IS NULL
            """,
            (
                current_time,
                current_time
            )
        )

        cleanup_counts[
            "support_anonymized"
        ] = support_cursor.rowcount or 0

        # ====================================================
        # ===== SUPPORT REQUEST ANONYMIZATION END =====
        # ====================================================


        # ====================================================
        # ===== ABUSE REPORT ANONYMIZATION START =====
        # ====================================================

        abuse_cursor = connection.execute(
            """
            UPDATE report_abuse

            SET
                full_name = 'Anonymized User',
                email = 'anonymized@invalid.local',
                access_code = NULL,
                subject = 'Anonymized abuse report',
                description = 'Personal data removed after retention period.',
                anonymized_at = ?

            WHERE
                retention_until IS NOT NULL
                AND retention_until <= ?
                AND anonymized_at IS NULL
                AND legal_hold = FALSE
            """,
            (
                current_time,
                current_time
            )
        )

        cleanup_counts[
            "abuse_anonymized"
        ] = abuse_cursor.rowcount or 0

        # ====================================================
        # ===== ABUSE REPORT ANONYMIZATION END =====
        # ====================================================


        # ====================================================
        # ===== PRIVACY REQUEST ANONYMIZATION START =====
        # ====================================================

        privacy_cursor = connection.execute(
            """
            UPDATE privacy_requests

            SET
                full_name = 'Anonymized User',
                email = 'anonymized@invalid.local',
                access_code = NULL,
                request_details = 'Personal data removed after retention period.',
                rejection_reason = NULL,
                anonymized_at = ?

            WHERE
                retention_until IS NOT NULL
                AND retention_until <= ?
                AND anonymized_at IS NULL
            """,
            (
                current_time,
                current_time
            )
        )

        cleanup_counts[
            "privacy_anonymized"
        ] = privacy_cursor.rowcount or 0

        # ====================================================
        # ===== PRIVACY REQUEST ANONYMIZATION END =====
        # ====================================================


        # ====================================================
        # ===== EXPIRED AUDIT LOG DELETE START =====
        # ====================================================

        audit_cursor = connection.execute(
            """
            DELETE FROM audit_logs

            WHERE
                retention_until IS NOT NULL
                AND retention_until <= ?
            """,
            (
                current_time,
            )
        )

        cleanup_counts[
            "audit_deleted"
        ] = audit_cursor.rowcount or 0

        # ====================================================
        # ===== EXPIRED AUDIT LOG DELETE END =====
        # ====================================================


        connection.commit()

    except Exception as error:

        if connection is not None:

            try:

                connection.rollback()

            except Exception:

                pass

        print(
            "GDPR personal data cleanup failed:",
            error
        )

    finally:

        if connection is not None:

            connection.close()

    return cleanup_counts

# ============================================================
# ===== GDPR PERSONAL DATA RETENTION CLEANUP END =====
# ============================================================
# ===== 18. PERIODIC CLEANUP BEFORE REQUEST START =====

@app.before_request
def run_periodic_cleanup():

    global last_cleanup_timestamp

    current_timestamp = time.time()

    time_since_last_cleanup = (
        current_timestamp
        -
        last_cleanup_timestamp
    )

    if (
        time_since_last_cleanup
        >=
        CLEANUP_INTERVAL_SECONDS
    ):

        cleanup_expired_files()
        cleanup_expired_personal_data()

        last_cleanup_timestamp = (
            current_timestamp
        )

# ===== 18. PERIODIC CLEANUP BEFORE REQUEST END =====


# ===== 19. QR CODE GENERATOR START =====

def generate_qr_code_data(access_url):

    qr_image = qrcode.make(
        access_url
    )

    image_buffer = BytesIO()

    qr_image.save(
        image_buffer,
        format="PNG"
    )

    encoded_image = base64.b64encode(
        image_buffer.getvalue()
    ).decode("utf-8")

    return (
        "data:image/png;base64,"
        +
        encoded_image
    )

# ===== 19. QR CODE GENERATOR END =====


# ===== 20. PIN LOCK STATUS CHECK START =====

def get_pin_lock_remaining_seconds(file_record):

    locked_until = file_record["locked_until"]

    if not locked_until:

        return 0

    lock_expiry = datetime.fromisoformat(
        locked_until
    )

    remaining_seconds = int(
        (
            lock_expiry
            -
            datetime.now()
        ).total_seconds()
    )

    if remaining_seconds <= 0:

        reset_pin_security(
            file_record["id"]
        )

        return 0

    return remaining_seconds

# ===== 20. PIN LOCK STATUS CHECK END =====


# ===== 21. REGISTER WRONG PIN START =====

def register_wrong_pin(file_record):

    current_attempts = (
        file_record["failed_pin_attempts"]
        or 0
    )

    new_attempts = current_attempts + 1

    locked_until = None

    if new_attempts >= MAX_PIN_ATTEMPTS:

        locked_until = (
            datetime.now()
            +
            timedelta(
                minutes=PIN_LOCK_MINUTES
            )
        ).isoformat()

    connection = get_database_connection()

    connection.execute(
        """
        UPDATE files
        SET
            failed_pin_attempts = ?,
            locked_until = ?
        WHERE id = ?
        """,
        (
            new_attempts,
            locked_until,
            file_record["id"]
        )
    )

    connection.commit()

    connection.close()

    return new_attempts

# ===== 21. REGISTER WRONG PIN END =====


# ===== 22. RESET PIN SECURITY START =====

def reset_pin_security(file_id):

    connection = get_database_connection()

    connection.execute(
        """
        UPDATE files
        SET
            failed_pin_attempts = 0,
            locked_until = NULL
        WHERE id = ?
        """,
        (file_id,)
    )

    connection.commit()

    connection.close()

# ===== 22. RESET PIN SECURITY END =====

# ============================================================
# ===== SUPPORT REQUESTS TABLE START =====
# ============================================================

def create_support_requests_table():

    connection = get_database_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS support_requests (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            ticket_id TEXT UNIQUE,

            name TEXT NOT NULL,

            email TEXT NOT NULL,

            access_code TEXT,

            problem_type TEXT NOT NULL,

            subject TEXT NOT NULL,

            message TEXT NOT NULL,

            created_at TEXT NOT NULL,

            status TEXT DEFAULT 'pending'

        )
        """
    )

    connection.commit()

    connection.close()

# ============================================================
# ===== SUPPORT REQUESTS TABLE END =====
# ============================================================

# ============================================================
# ===== GDPR AUDIT LOG HELPER START =====
# ============================================================

def create_audit_log(
    event_type,
    entity_type,
    entity_id,
    action,
    event_details=None,
    actor_type="admin",
    actor_identifier=None
):

    connection = None

    try:

        connection = get_database_connection()

        connection.execute(
            """
            INSERT INTO audit_logs (

                event_type,
                entity_type,
                entity_id,
                action,
                actor_type,
                actor_identifier,
                event_details,
                ip_address,
                created_at,
                retention_until

            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                entity_type,
                str(entity_id) if entity_id is not None else None,
                action,
                actor_type,
                actor_identifier,
                event_details,
                request.remote_addr,
                datetime.now().isoformat(),
                (
                    datetime.now()
                    +
                    timedelta(
                        days=AUDIT_LOG_RETENTION_DAYS
                    )
                ).isoformat()
            )
        )

        connection.commit()

        return True

    except Exception as error:

        if connection is not None:

            try:
                connection.rollback()

            except Exception:
                pass

        print(
            "Audit log creation failed:",
            error
        )

        return False

    finally:

        if connection is not None:
            connection.close()

# ============================================================
# ===== GDPR AUDIT LOG HELPER END =====
# ============================================================
# ============================================================
# ===== SECURITY RESPONSE HEADERS START =====
# ============================================================

@app.after_request
def add_security_headers(response):

    # Browser ko MIME type guess karne se rokta hai.
    response.headers.setdefault(
        "X-Content-Type-Options",
        "nosniff"
    )

    # Fyloq ko iframe me embed karke clickjacking rokta hai.
    response.headers.setdefault(
        "X-Frame-Options",
        "DENY"
    )

    # External pages ko unnecessary referrer information kam deta hai.
    response.headers.setdefault(
        "Referrer-Policy",
        "strict-origin-when-cross-origin"
    )

    # Camera, microphone aur geolocation access disable karta hai.
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()"
    )

    response.headers.setdefault(
        "Cross-Origin-Opener-Policy",
        "same-origin"
    )

    response.headers.setdefault(
        "Cross-Origin-Resource-Policy",
        "same-origin"
    )

    # Production HTTPS par browser ko HTTPS prefer karne bolta hai.
    if IS_PRODUCTION:

        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains"
        )

    # Admin pages browser cache me save nahi honge.
    if request.path.startswith(
        "/admin"
    ):

        response.headers[
            "Cache-Control"
        ] = (
            "no-store, no-cache, must-revalidate, "
            "private, max-age=0"
        )

        response.headers[
            "Pragma"
        ] = "no-cache"

    return response

# ============================================================
# ===== SECURITY RESPONSE HEADERS END =====
# ============================================================

# ===== 23. HOME ROUTE START =====

@app.route("/")
def home():

    return render_template(
        "index.html"
    )

# ===== 23. HOME ROUTE END =====

# ============================================================
# ===== SUPPORT PAGE ROUTE START =====
# ============================================================

@app.route(
    "/support",
    methods=["GET", "POST"]
)
@limiter.limit("5 per hour")
def support_page():

    success_message = None

    error_message = None

    ticket_id = None

    if request.method == "POST":

        # ===== SUPPORT FORM DATA START =====

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        access_code = request.form.get(
            "access_code",
            ""
        ).strip()

        problem_type = request.form.get(
            "problem_type",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        support_message = request.form.get(
            "message",
            ""
        ).strip()

        support_consent = request.form.get(
            "support_consent",
            ""
        )

        # ===== SUPPORT FORM DATA END =====


        # ===== SUPPORT FORM VALIDATION START =====

        if not name:

            error_message = (
                "Please enter your name."
            )

        elif len(name) > 80:

            error_message = (
                "Name is too long."
            )

        elif (
            not email
            or
            "@" not in email
            or
            "." not in email.split("@")[-1]
        ):

            error_message = (
                "Please enter a valid email address."
            )

        elif len(email) > 120:

            error_message = (
                "Email address is too long."
            )

        elif (
            access_code
            and
            not (
                access_code.isdigit()
                and
                len(access_code) == 6
            )
        ):

            error_message = (
                "Access code must contain exactly 6 digits."
            )

        elif not problem_type:

            error_message = (
                "Please select a problem type."
            )

        elif not subject:

            error_message = (
                "Please enter a subject."
            )

        elif len(subject) > 150:

            error_message = (
                "Subject is too long."
            )

        elif not support_message:

            error_message = (
                "Please describe your problem."
            )

        elif len(support_message) > 2000:

            error_message = (
                "Problem description cannot exceed 2000 characters."
            )

        elif support_consent != "yes":

            error_message = (
                "Please accept the support request consent."
            )

        # ===== SUPPORT FORM VALIDATION END =====


        # ===== SAVE SUPPORT REQUEST START =====

        if error_message is None:

            created_at = datetime.now()

            connection = get_database_connection()

            cursor = connection.execute(
                """
                INSERT INTO support_requests (

                    ticket_id,
                    name,
                    email,
                    access_code,
                    problem_type,
                    subject,
                    message,
                    created_at,
                    status

                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    name,
                    email,
                    access_code or None,
                    problem_type,
                    subject,
                    support_message,
                    created_at.isoformat(),
                    "pending"
                )
            )

            request_id = cursor.lastrowid

            ticket_id = (
                "FY-"
                +
                created_at.strftime(
                    "%Y%m%d"
                )
                +
                "-"
                +
                str(request_id).zfill(5)
            )

            connection.execute(
                """
                UPDATE support_requests
                SET ticket_id = ?
                WHERE id = ?
                """,
                (
                    ticket_id,
                    request_id
                )
            )

            connection.commit()

            connection.close()

            success_message = (
                "Your support request has been submitted successfully. "
                "Our support team will review it and contact you through email."
            )

        # ===== SAVE SUPPORT REQUEST END =====


    return render_template(
        "support.html",

        success_message=success_message,

        error_message=error_message,

        ticket_id=ticket_id
    )

# ============================================================
# ===== SUPPORT PAGE ROUTE END =====
# ============================================================

# ============================================================
# ===== PRIVACY PAGE ROUTE START =====
# ============================================================

@app.route("/privacy")
def privacy_page():

    return render_template(
        "privacy.html"
    )

# ============================================================
# ===== PRIVACY PAGE ROUTE END =====
# ============================================================
# ============================================================
# ===== GDPR PRIVACY REQUEST PAGE ROUTE START =====
# ============================================================

@app.route(
    "/privacy-request",
    methods=["GET", "POST"]
)
@limiter.limit("5 per hour")
def privacy_request_page():

    success_message = None
    error_message = None
    request_reference = None

    allowed_request_types = {
        "access",
        "rectification",
        "erasure",
        "restriction",
        "objection",
        "portability"
    }

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        request_type = request.form.get(
            "request_type",
            ""
        ).strip().lower()

        access_code = request.form.get(
            "access_code",
            ""
        ).strip()

        request_details = request.form.get(
            "request_details",
            ""
        ).strip()

        declaration = request.form.get(
            "declaration",
            ""
        )

        # ====================================================
        # ===== PRIVACY REQUEST VALIDATION START =====
        # ====================================================

        if not full_name:

            error_message = (
                "Please enter your full name."
            )

        elif len(full_name) > 80:

            error_message = (
                "Full name cannot exceed 80 characters."
            )

        elif (
            not email
            or
            "@" not in email
            or
            "." not in email.split("@")[-1]
        ):

            error_message = (
                "Please enter a valid email address."
            )

        elif len(email) > 120:

            error_message = (
                "Email address cannot exceed 120 characters."
            )

        elif request_type not in allowed_request_types:

            error_message = (
                "Please select a valid privacy request type."
            )

        elif (
            access_code
            and
            not (
                access_code.isdigit()
                and
                len(access_code) == 6
            )
        ):

            error_message = (
                "Access code must contain exactly 6 digits."
            )

        elif not request_details:

            error_message = (
                "Please explain your privacy request."
            )

        elif len(request_details) > 3000:

            error_message = (
                "Request details cannot exceed 3000 characters."
            )

        elif declaration != "yes":

            error_message = (
                "Please confirm the declaration."
            )

        # ====================================================
        # ===== PRIVACY REQUEST VALIDATION END =====
        # ====================================================


        # ====================================================
        # ===== SAVE PRIVACY REQUEST START =====
        # ====================================================

        if error_message is None:

            submitted_at = datetime.now()

            response_due_at = (
                submitted_at
                +
                timedelta(
                    days=30
                )
            )

            request_reference = (
                "FY-PR-"
                +
                submitted_at.strftime(
                    "%Y%m%d"
                )
                +
                "-"
                +
                secrets.token_hex(
                    4
                ).upper()
            )

            connection = None

            try:

                connection = get_database_connection()

                connection.execute(
                    """
                    INSERT INTO privacy_requests (

                        request_reference,
                        full_name,
                        email,
                        request_type,
                        access_code,
                        request_details,
                        identity_status,
                        status,
                        rejection_reason,
                        submitted_at,
                        response_due_at,
                        completed_at,
                        updated_at

                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        request_reference,
                        full_name,
                        email,
                        request_type,
                        access_code or None,
                        request_details,
                        "pending",
                        "pending",
                        None,
                        submitted_at.isoformat(),
                        response_due_at.isoformat(),
                        None,
                        submitted_at.isoformat()
                    )
                )

                connection.commit()
                create_audit_log(
                    event_type="privacy_request_submission",
                    entity_type="privacy_request",
                    entity_id=request_reference,
                    action="request_submitted",
                    actor_type="user",
                    actor_identifier=None,
                    event_details=(
                        f"Privacy request type: {request_type}"
                    )
                )
                success_message = (
                    "Your privacy request was submitted successfully. "
                    "Please save the reference number shown below. "
                    "Fyloq may contact you for identity verification."
                )

            except Exception as error:

                if connection is not None:

                    try:

                        connection.rollback()

                    except Exception:

                        pass

                print(
                    "Privacy request submission failed:",
                    error
                )

                request_reference = None

                error_message = (
                    "Your privacy request could not be submitted. "
                    "Please try again."
                )

            finally:

                if connection is not None:

                    connection.close()

        # ====================================================
        # ===== SAVE PRIVACY REQUEST END =====
        # ====================================================

    return render_template(
        "privacy_request.html",

        success_message=success_message,

        error_message=error_message,

        request_reference=request_reference
    )

# ============================================================
# ===== GDPR PRIVACY REQUEST PAGE ROUTE END =====
# ============================================================
# ============================================================
# ===== TERMS PAGE ROUTE START =====
# ============================================================

@app.route("/terms")
def terms_page():

    return render_template(
        "terms.html"
    )

# ============================================================
# ===== TERMS PAGE ROUTE END =====
# ============================================================

# ============================================================
# ===== LEGAL NOTICE PAGE ROUTE START =====
# ============================================================

@app.route("/legal")
def legal_page():

    return render_template(
        "legal.html"
    )

# ============================================================
# ===== LEGAL NOTICE PAGE ROUTE END =====
# ============================================================

# ============================================================
# ===== REPORT ABUSE PAGE ROUTE START =====
# ============================================================

@app.route(
    "/report-abuse",
    methods=["GET", "POST"]
)
@limiter.limit("5 per hour")
def report_abuse_page():

    success_message = None

    error_message = None

    complaint_id = None


    # ===== REPORT ABUSE FORM SUBMIT START =====

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        access_code = request.form.get(
            "access_code",
            ""
        ).strip()

        complaint_type = request.form.get(
            "complaint_type",
            ""
        ).strip().lower()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        declaration = request.form.get(
            "declaration",
            ""
        )


        # ===== ALLOWED COMPLAINT TYPES START =====

        allowed_complaint_types = {
            "copyright",
            "malware",
            "privacy",
            "fraud",
            "harassment",
            "illegal_content",
            "security",
            "other"
        }

        # ===== ALLOWED COMPLAINT TYPES END =====


        # ===== FORM VALIDATION START =====

        if not full_name:

            error_message = (
                "Please enter your full name."
            )

        elif len(full_name) > 80:

            error_message = (
                "Full name cannot exceed 80 characters."
            )

        elif (
            not email
            or
            "@" not in email
            or
            "." not in email.split("@")[-1]
        ):

            error_message = (
                "Please enter a valid email address."
            )

        elif len(email) > 120:

            error_message = (
                "Email address cannot exceed 120 characters."
            )

        elif (
            access_code
            and
            not (
                access_code.isdigit()
                and
                len(access_code) == 6
            )
        ):

            error_message = (
                "Access code must contain exactly 6 digits."
            )

        elif (
            complaint_type
            not in allowed_complaint_types
        ):

            error_message = (
                "Please select a valid complaint type."
            )

        elif not subject:

            error_message = (
                "Please enter the complaint subject."
            )

        elif len(subject) > 150:

            error_message = (
                "Subject cannot exceed 150 characters."
            )

        elif not description:

            error_message = (
                "Please describe the complaint."
            )

        elif len(description) > 3000:

            error_message = (
                "Complaint description cannot exceed 3000 characters."
            )

        elif declaration != "yes":

            error_message = (
                "Please confirm the complaint declaration."
            )

        # ===== FORM VALIDATION END =====


        # ===== SAVE COMPLAINT START =====

        if error_message is None:

            created_at = datetime.now()

            connection = get_database_connection()

            cursor = connection.execute(
                """
                INSERT INTO report_abuse (

                    full_name,
                    email,
                    access_code,
                    complaint_type,
                    subject,
                    description,
                    status,
                    created_at

                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    full_name,
                    email,
                    access_code or None,
                    complaint_type,
                    subject,
                    description,
                    "Pending",
                    created_at.isoformat()
                )
            )

            report_id = cursor.lastrowid

            connection.commit()

            connection.close()

            complaint_id = (
                "FY-AB-"
                +
                str(report_id).zfill(6)
            )

            success_message = (
                "Your abuse report has been submitted successfully. "
                "Our team will review the complaint and contact you "
                "through the email address provided."
            )

        # ===== SAVE COMPLAINT END =====

    # ===== REPORT ABUSE FORM SUBMIT END =====


    return render_template(
        "report_abuse.html",

        success_message=success_message,

        error_message=error_message,

        complaint_id=complaint_id
    )

# ============================================================
# ===== REPORT ABUSE PAGE ROUTE END =====
# ============================================================


# ============================================================
# ===== ADMIN PASSWORD VERIFICATION HELPER START =====
# ============================================================

def verify_admin_password(password):

    # Production ke liye hashed password preferred hai.
    if ADMIN_PASSWORD_HASH:

        return check_password_hash(
            ADMIN_PASSWORD_HASH,
            password
        )

    # Plain environment-password fallback ke liye
    # timing-safe comparison use hota hai.
    return hmac.compare_digest(
        password,
        ADMIN_PASSWORD
    )

# ============================================================
# ===== ADMIN PASSWORD VERIFICATION HELPER END =====
# ============================================================

# ============================================================
# ===== 24. ADMIN LOGIN ROUTE START =====
# ============================================================

@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
@limiter.limit("10 per 15 minutes")
def admin_login():

    global admin_failed_login_attempts

    global admin_login_locked_until


    # ===== ALREADY LOGGED-IN CHECK START =====

    if session.get("admin_logged_in"):

        return redirect(
            url_for("admin_dashboard")
        )

    # ===== ALREADY LOGGED-IN CHECK END =====


    error = None


    # ===== ADMIN LOCK CHECK START =====

    if admin_login_locked_until:

        remaining_seconds = int(
            (
                admin_login_locked_until
                -
                datetime.now()
            ).total_seconds()
        )

        if remaining_seconds > 0:

            remaining_minutes = max(
                1,
                (
                    remaining_seconds + 59
                ) // 60
            )

            error = (
                "Too many incorrect login attempts. "
                f"Try again after {remaining_minutes} minute(s)."
            )

            return render_template(
                "admin_login.html",
                error=error
            )

        admin_failed_login_attempts = 0

        admin_login_locked_until = None

    # ===== ADMIN LOCK CHECK END =====


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        # ===== EMPTY FIELD VALIDATION START =====

        if not username or not password:

            error = (
                "Please enter both username and password."
            )

            return render_template(
                "admin_login.html",
                error=error
            )

        # ===== EMPTY FIELD VALIDATION END =====


        # ===== SUCCESSFUL LOGIN START =====

        if (
            hmac.compare_digest(
                username,
                ADMIN_USERNAME
            )
            and
            verify_admin_password(
                password
            )
        ):

            admin_failed_login_attempts = 0

            admin_login_locked_until = None

            session.clear()

            session["admin_logged_in"] = True

            session.permanent = True
            create_audit_log(
                event_type="admin_login",
                entity_type="admin_session",
                entity_id=ADMIN_USERNAME,
                action="login_successful",
                actor_type="admin",
                actor_identifier=ADMIN_USERNAME,
                event_details=(
                    "Administrator logged in successfully."
                )
            )
            return redirect(
                url_for("admin_dashboard")
            )

        # ===== SUCCESSFUL LOGIN END =====


        # ===== FAILED LOGIN START =====

        admin_failed_login_attempts += 1

        attempts_left = (
            MAX_ADMIN_LOGIN_ATTEMPTS
            -
            admin_failed_login_attempts
        )

        if attempts_left <= 0:

            admin_login_locked_until = (
                datetime.now()
                +
                timedelta(
                    minutes=ADMIN_LOGIN_LOCK_MINUTES
                )
            )

            error = (
                "Too many incorrect login attempts. "
                f"Admin login is locked for "
                f"{ADMIN_LOGIN_LOCK_MINUTES} minutes."
            )

        else:

            error = (
                "Incorrect admin username or password. "
                f"{attempts_left} attempt(s) remaining."
            )

        # ===== FAILED LOGIN END =====


    return render_template(
        "admin_login.html",
        error=error
    )

# ============================================================
# ===== 24. ADMIN LOGIN ROUTE END =====
# ===========================================================================


# ============================================================
# ===== 25. ADMIN DASHBOARD ROUTE START =====
# ============================================================

@app.route("/admin")
def admin_dashboard():

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("admin_login")
        )

    # ===== SEARCH AND STATUS FILTER START =====

    search_query = request.args.get(
        "search",
        ""
    ).strip()

    status_filter = request.args.get(
        "status",
        "all"
    ).strip().lower()

    allowed_status_filters = {
        "all",
        "active",
        "expired",
        "downloaded",
        "missing"
    }

    if status_filter not in allowed_status_filters:

        status_filter = "all"

    # ===== SEARCH AND STATUS FILTER END =====

    connection = get_database_connection()

    # ===== FILE QUERY START =====

    query_conditions = []

    query_values = []

    if search_query:

        query_conditions.append(
            """
            (
                original_filename LIKE ?
                OR
                access_code LIKE ?
            )
            """
        )

        query_values.extend(
            [
                f"%{search_query}%",
                f"%{search_query}%"
            ]
        )

    if status_filter != "all":

        query_conditions.append(
            "status = ?"
        )

        query_values.append(
            status_filter
        )

    file_query = """
        SELECT *
        FROM files
    """

    if query_conditions:

        file_query += (
            " WHERE "
            +
            " AND ".join(
                query_conditions
            )
        )

    file_query += " ORDER BY id DESC"

    files = connection.execute(
        file_query,
        tuple(query_values)
    ).fetchall()

    # ===== FILE QUERY END =====

    # ===== TOTAL UPLOADS START =====

    total_uploads = connection.execute(
        """
        SELECT COUNT(*)
        FROM files
        """
    ).fetchone()[0]

    # ===== TOTAL UPLOADS END =====

    # ===== ACTIVE FILES START =====

    active_files = connection.execute(
        """
        SELECT COUNT(*)
        FROM files
        WHERE status = 'active'
        """
    ).fetchone()[0]

    # ===== ACTIVE FILES END =====

    # ===== EXPIRED FILES START =====

    expired_files = connection.execute(
        """
        SELECT COUNT(*)
        FROM files
        WHERE status = 'expired'
        """
    ).fetchone()[0]

    # ===== EXPIRED FILES END =====

    # ===== TOTAL DOWNLOADS START =====

    total_downloads = connection.execute(
        """
        SELECT
        COALESCE(
            SUM(download_count),
            0
        )
        FROM files
        """
    ).fetchone()[0]

    # ===== TOTAL DOWNLOADS END =====

    # ===== TOTAL STORAGE START =====

    total_storage = connection.execute(
        """
        SELECT
        COALESCE(
            SUM(file_size),
            0
        )
        FROM files
        """
    ).fetchone()[0]

    # ===== TOTAL STORAGE END =====

    # ===== ACTIVE STORAGE START =====

    active_storage = connection.execute(
        """
        SELECT
        COALESCE(
            SUM(file_size),
            0
        )
        FROM files
        WHERE status = 'active'
        """
    ).fetchone()[0]

    # ===== ACTIVE STORAGE END =====

    # ===== SUPPORT REQUEST COUNT START =====

    total_support_requests = connection.execute(
        """
        SELECT COUNT(*)
        FROM support_requests
        """
    ).fetchone()[0]

    pending_support_requests = connection.execute(
    """
    SELECT COUNT(*)
    FROM support_requests
    WHERE LOWER(status) = 'pending'
    """
).fetchone()[0]

    # ===== SUPPORT REQUEST COUNT END =====


    # ===== ABUSE REPORT COUNT START =====

    total_abuse_reports = connection.execute(
        """
        SELECT COUNT(*)
        FROM report_abuse
        """
    ).fetchone()[0]

    pending_abuse_reports = connection.execute(
        """
        SELECT COUNT(*)
        FROM report_abuse
        WHERE LOWER(status) = 'pending'
        """
    ).fetchone()[0]

    # ===== ABUSE REPORT COUNT END =====

    connection.close()

    # ===== STORAGE PERCENTAGE START =====

    storage_limit = (
        FYLOQ_STORAGE_LIMIT
    )

    storage_percentage = round(
        (
            total_storage
            /
            storage_limit
        )
        *
        100,
        1
    )

    if storage_percentage > 100:

        storage_percentage = 100

    # ===== STORAGE PERCENTAGE END =====

    # ===== FILE FORMAT LOOP START =====

    formatted_files = []

    for file_record in files:

        formatted_file = dict(
            file_record
        )

        formatted_file[
            "formatted_size"
        ] = format_size(
            file_record["file_size"]
        )

        try:

            formatted_file[
                "formatted_expiry"
            ] = datetime.fromisoformat(
                file_record["expires_at"]
            ).strftime(
                "%d %b %Y %I:%M %p"
            )

        except (
            TypeError,
            ValueError
        ):

            formatted_file[
                "formatted_expiry"
            ] = "Unknown"

        formatted_files.append(
            formatted_file
        )

    # ===== FILE FORMAT LOOP END =====

    return render_template(

        "admin_dashboard.html",

        total_uploads=total_uploads,

        active_files=active_files,

        expired_files=expired_files,

        total_downloads=total_downloads,
        total_support_requests=total_support_requests,

        pending_support_requests=pending_support_requests,

        total_abuse_reports=total_abuse_reports,

        pending_abuse_reports=pending_abuse_reports,

        storage_used=format_size(
            total_storage
        ),

        active_storage=format_size(
            active_storage
        ),

        storage_percentage=storage_percentage,

        files=formatted_files,

        search_query=search_query,

        status_filter=status_filter,

        message=request.args.get(
            "message"
        )

    )

# ============================================================
# ===== 25. ADMIN DASHBOARD ROUTE END =====
# ============================================================


# ============================================================
# ===== 26. ADMIN CLEANUP FILES ROUTE START =====
# ============================================================

@app.route(
    "/admin/cleanup-files",
    methods=["POST"]
)
def admin_cleanup_files():

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("admin_login")
        )

    cleanup_result = (
        permanently_delete_expired_files()
    )

    deleted_count = cleanup_result[
        "deleted_count"
    ]

    deleted_storage = cleanup_result[
        "deleted_storage"
    ]

    return redirect(
        url_for(
            "admin_dashboard",
            message=(
                f"{deleted_count} expired file record(s) "
                f"permanently deleted. "
                f"{format_size(deleted_storage)} storage cleared."
            )
        )
    )

# ============================================================
# ===== 26. ADMIN CLEANUP FILES ROUTE END =====
# ============================================================


# ============================================================
# ===== 27. ADMIN DELETE FILE ROUTE START =====
# ============================================================

@app.route(
    "/admin/delete-file/<int:file_id>",
    methods=["POST"]
)
def admin_delete_file(file_id):

    if not session.get("admin_logged_in"):
        
        return redirect(
            url_for("admin_login")
        )

    # ============================================================
    # ===== GET FILE RECORD START =====
    # ============================================================

    connection = get_database_connection()

    file_record = connection.execute(
        """
        SELECT *
        FROM files
        WHERE id = ?
        """,
        (file_id,)
    ).fetchone()

    connection.close()

    if file_record is None:

        return redirect(
            url_for(
                "admin_dashboard",
                message="File record not found."
            )
        )

    # ============================================================
    # ===== GET FILE RECORD END =====
    # ============================================================


    # ============================================================
    # ===== SUPABASE STORAGE DELETE START =====
    # ============================================================

    try:

        delete_file_from_storage(
            file_record["stored_filename"]
        )

    except Exception as error:

        error_text = str(
            error
        ).lower()

        # Storage file already missing ho,
        # to DB record delete continue kar sakte hain.
        if not (
            "404" in error_text
            or
            "not found" in error_text
        ):

            print(
                "Admin Storage delete failed:",
                error
            )

            return redirect(
                url_for(
                    "admin_dashboard",
                    message=(
                        "File could not be deleted from Storage. "
                        "Database record was preserved."
                    )
                )
            )

    # ============================================================
    # ===== SUPABASE STORAGE DELETE END =====
    # ============================================================


    # ============================================================
    # ===== DATABASE RECORD DELETE START =====
    # ============================================================

    connection = get_database_connection()

    try:

        connection.execute(
            """
            DELETE FROM files
            WHERE id = ?
            """,
            (file_id,)
        )

        connection.commit()

    except Exception as error:

        try:

            connection.rollback()

        except Exception:

            pass

        print(
            "Admin database delete failed:",
            error
        )

        # Storage delete ho chuki hai lekin DB record
        # delete nahi hua, to record ko missing mark karo.
        try:

            connection.execute(
                """
                UPDATE files
                SET status = 'missing'
                WHERE id = ?
                """,
                (file_id,)
            )

            connection.commit()

        except Exception as update_error:

            try:

                connection.rollback()

            except Exception:

                pass

            print(
                "Could not mark deleted file as missing:",
                update_error
            )

        return redirect(
            url_for(
                "admin_dashboard",
                message=(
                    "File was removed from Storage, "
                    "but database cleanup could not be completed."
                )
            )
        )

    finally:

        connection.close()

    # ============================================================
    # ===== DATABASE RECORD DELETE END =====
    # ============================================================

    return redirect(
        url_for(
            "admin_dashboard",
            message=(
                "File and database record "
                "permanently deleted successfully."
            )
        )
    )

# ============================================================
# ===== 27. ADMIN DELETE FILE ROUTE END =====
# ============================================================
# ============================================================
# ===== ADMIN EXPIRE FILE ROUTE START =====
# ============================================================

@app.route(
    "/admin/expire-file/<int:file_id>",
    methods=["POST"]
)
def admin_expire_file(file_id):

    if not session.get("admin_logged_in"):
        


        return redirect(
            url_for("admin_login")
        )

    # ===== GET FILE RECORD START =====

    connection = get_database_connection()

    file_record = connection.execute(
        """
        SELECT *
        FROM files
        WHERE id = ?
        """,
        (file_id,)
    ).fetchone()

    connection.close()

    if file_record is None:

        return redirect(
            url_for(
                "admin_dashboard",
                message="File record not found."
            )
        )

    if file_record["status"] != "active":

        return redirect(
            url_for(
                "admin_dashboard",
                message="Only active files can be expired."
            )
        )

    # ===== GET FILE RECORD END =====


    # ===== SUPABASE STORAGE DELETE START =====

    try:

        delete_file_from_storage(
            file_record["stored_filename"]
        )

    except Exception as error:

        error_text = str(error).lower()

        if not (
            "404" in error_text
            or
            "not found" in error_text
        ):

            print(
                "Admin expire Storage delete failed:",
                error
            )

            return redirect(
                url_for(
                    "admin_dashboard",
                    message=(
                        "File could not be expired because "
                        "Storage deletion failed."
                    )
                )
            )

    # ===== SUPABASE STORAGE DELETE END =====


    # ===== DATABASE STATUS UPDATE START =====

    connection = get_database_connection()

    try:

        connection.execute(
            """
            UPDATE files
            SET status = 'expired'
            WHERE id = ?
            """,
            (file_id,)
        )

        connection.commit()
        create_audit_log(
            event_type="file_expiry",
            entity_type="uploaded_file",
            entity_id=file_id,
            action="manually_expired",
            actor_type="admin",
            actor_identifier=ADMIN_USERNAME,
            event_details=(
                "Administrator manually expired the file "
                "and removed its encrypted storage object."
            )
        )
    except Exception as error:

        try:

            connection.rollback()

        except Exception:

            pass

        print(
            "Admin expire database update failed:",
            error
        )

        return redirect(
            url_for(
                "admin_dashboard",
                message=(
                    "File was removed from Storage, "
                    "but database status update failed."
                )
            )
        )

    finally:

        connection.close()

    # ===== DATABASE STATUS UPDATE END =====


    return redirect(
        url_for(
            "admin_dashboard",
            message="File expired successfully."
        )
    )

# ============================================================
# ===== ADMIN EXPIRE FILE ROUTE END =====
# ============================================================

# ============================================================
# ===== ADMIN SUPPORT REQUESTS ROUTE START =====
# ============================================================

@app.route("/admin/support-requests")
def admin_support_requests():

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("admin_login")
        )

    search_query = request.args.get(
        "search",
        ""
    ).strip()

    status_filter = request.args.get(
        "status",
        "all"
    ).strip().lower()

    allowed_status_filters = {
        "all",
        "pending",
        "solved",
        "closed"
    }

    if status_filter not in allowed_status_filters:

        status_filter = "all"

    connection = get_database_connection()

    query_conditions = []

    query_values = []

    if search_query:

        query_conditions.append(
            """
            (
                ticket_id LIKE ?
                OR
                name LIKE ?
                OR
                email LIKE ?
                OR
                access_code LIKE ?
                OR
                subject LIKE ?
            )
            """
        )

        search_value = f"%{search_query}%"

        query_values.extend(
            [
                search_value,
                search_value,
                search_value,
                search_value,
                search_value
            ]
        )

    if status_filter != "all":

        query_conditions.append(
            "status = ?"
        )

        query_values.append(
            status_filter
        )

    support_query = """
        SELECT *
        FROM support_requests
    """

    if query_conditions:

        support_query += (
            " WHERE "
            +
            " AND ".join(
                query_conditions
            )
        )

    support_query += " ORDER BY id DESC"

    support_records = connection.execute(
        support_query,
        tuple(query_values)
    ).fetchall()

    total_requests = connection.execute(
        """
        SELECT COUNT(*)
        FROM support_requests
        """
    ).fetchone()[0]

    pending_requests = connection.execute(
        """
        SELECT COUNT(*)
        FROM support_requests
        WHERE status = 'pending'
        """
    ).fetchone()[0]

    solved_requests = connection.execute(
        """
        SELECT COUNT(*)
        FROM support_requests
        WHERE status = 'solved'
        """
    ).fetchone()[0]

    closed_requests = connection.execute(
        """
        SELECT COUNT(*)
        FROM support_requests
        WHERE status = 'closed'
        """
    ).fetchone()[0]

    connection.close()

    formatted_support_requests = []

    problem_type_names = {
        "forgot_pin": "Forgot File PIN",
        "access_code_not_working": "Access Code Not Working",
        "download_problem": "Download Problem",
        "upload_problem": "Upload Problem",
        "expired_file": "Expired or Unavailable File",
        "wrong_file": "Wrong or Suspicious File",
        "technical_problem": "Website Technical Problem",
        "other": "Other Problem"
    }

    for support_record in support_records:

        formatted_support = dict(
            support_record
        )

        formatted_support[
            "formatted_problem_type"
        ] = problem_type_names.get(
            support_record["problem_type"],
            support_record["problem_type"]
        )

        try:

            formatted_support[
                "formatted_created_at"
            ] = datetime.fromisoformat(
                support_record["created_at"]
            ).strftime(
                "%d %b %Y, %I:%M %p"
            )

        except (
            TypeError,
            ValueError
        ):

            formatted_support[
                "formatted_created_at"
            ] = "Unknown"

        formatted_support_requests.append(
            formatted_support
        )

    return render_template(
        "admin_support_requests.html",

        support_requests=formatted_support_requests,

        total_requests=total_requests,

        pending_requests=pending_requests,

        solved_requests=solved_requests,

        closed_requests=closed_requests,

        search_query=search_query,

        status_filter=status_filter,

        message=request.args.get(
            "message"
        )
    )

# ============================================================
# ===== ADMIN SUPPORT REQUESTS ROUTE END =====
# ============================================================


# ============================================================
# ===== ADMIN UPDATE SUPPORT STATUS ROUTE START =====
# ============================================================

@app.route(
    "/admin/support-requests/<int:request_id>/status",
    methods=["POST"]
)
def admin_update_support_status(request_id):

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("admin_login")
        )

    new_status = request.form.get(
        "status",
        ""
    ).strip().lower()

    allowed_statuses = {
        "pending",
        "solved",
        "closed"
    }

    if new_status not in allowed_statuses:

        return redirect(
            url_for(
                "admin_support_requests",
                message="Invalid support status."
            )
        )

    connection = get_database_connection()

    support_record = connection.execute(
        """
        SELECT id
        FROM support_requests
        WHERE id = ?
        """,
        (request_id,)
    ).fetchone()

    if support_record is None:

        connection.close()

        return redirect(
            url_for(
                "admin_support_requests",
                message="Support request not found."
            )
        )

    updated_at = datetime.now()

    resolved_at = None
    closed_at = None
    retention_until = None

    if new_status == "solved":

        resolved_at = updated_at.isoformat()

    elif new_status == "closed":

        closed_at = updated_at.isoformat()

        retention_until = (
            updated_at
            +
            timedelta(
                days=SUPPORT_RETENTION_DAYS
            )
        ).isoformat()

    connection.execute(
        """
        UPDATE support_requests

        SET
            status = ?,
            resolved_at = CASE
                WHEN ? IS NOT NULL
                THEN ?
                ELSE resolved_at
            END,
            closed_at = CASE
                WHEN ? IS NOT NULL
                THEN ?
                ELSE closed_at
            END,
            retention_until = CASE
                WHEN ? IS NOT NULL
                THEN ?
                ELSE retention_until
            END

        WHERE id = ?
        """,
        (
            new_status,

            resolved_at,
            resolved_at,

            closed_at,
            closed_at,

            retention_until,
            retention_until,

            request_id
        )
    )

    connection.commit()

    create_audit_log(
        event_type="support_request_update",
        entity_type="support_request",
        entity_id=request_id,
        action="status_updated",
        actor_type="admin",
        actor_identifier=ADMIN_USERNAME,
        event_details=(
            f"Support request status changed to: {new_status}"
        )
    )

    connection.close()

    return redirect(
        url_for(
            "admin_support_requests",
            message="Support request status updated."
        )
    )

# ============================================================
# ===== ADMIN UPDATE SUPPORT STATUS ROUTE END =====
# ============================================================

# ============================================================
# ===== ADMIN ABUSE REPORTS ROUTE START =====
# ============================================================

@app.route("/admin/abuse-reports")
def admin_abuse_reports():

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("admin_login")
        )


    # ===== SEARCH AND STATUS FILTER START =====

    search_query = request.args.get(
        "search",
        ""
    ).strip()

    status_filter = request.args.get(
        "status",
        "all"
    ).strip().lower()

    allowed_status_filters = {
        "all",
        "pending",
        "investigating",
        "resolved",
        "closed"
    }

    if status_filter not in allowed_status_filters:

        status_filter = "all"

    # ===== SEARCH AND STATUS FILTER END =====


    connection = get_database_connection()


    # ===== ABUSE REPORT QUERY START =====

    query_conditions = []

    query_values = []

    if search_query:

        query_conditions.append(
            """
            (
                full_name LIKE ?
                OR
                email LIKE ?
                OR
                access_code LIKE ?
                OR
                complaint_type LIKE ?
                OR
                subject LIKE ?
                OR
                description LIKE ?
            )
            """
        )

        search_value = (
            f"%{search_query}%"
        )

        query_values.extend(
            [
                search_value,
                search_value,
                search_value,
                search_value,
                search_value,
                search_value
            ]
        )

    if status_filter != "all":

        query_conditions.append(
            "LOWER(status) = ?"
        )

        query_values.append(
            status_filter
        )

    abuse_query = """
        SELECT *
        FROM report_abuse
    """

    if query_conditions:

        abuse_query += (
            " WHERE "
            +
            " AND ".join(
                query_conditions
            )
        )

    abuse_query += (
        " ORDER BY id DESC"
    )

    abuse_records = connection.execute(
        abuse_query,
        tuple(query_values)
    ).fetchall()

    # ===== ABUSE REPORT QUERY END =====


    # ===== ABUSE REPORT STATISTICS START =====

    total_reports = connection.execute(
        """
        SELECT COUNT(*)
        FROM report_abuse
        """
    ).fetchone()[0]

    pending_reports = connection.execute(
        """
        SELECT COUNT(*)
        FROM report_abuse
        WHERE LOWER(status) = 'pending'
        """
    ).fetchone()[0]

    investigating_reports = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM report_abuse
            WHERE LOWER(status) = 'investigating'
            """
        ).fetchone()[0]
    )

    resolved_reports = connection.execute(
        """
        SELECT COUNT(*)
        FROM report_abuse
        WHERE LOWER(status) = 'resolved'
        """
    ).fetchone()[0]

    closed_reports = connection.execute(
        """
        SELECT COUNT(*)
        FROM report_abuse
        WHERE LOWER(status) = 'closed'
        """
    ).fetchone()[0]

    # ===== ABUSE REPORT STATISTICS END =====


    connection.close()


    # ===== COMPLAINT TYPE NAMES START =====

    complaint_type_names = {

        "copyright":
            "Copyright Violation",

        "malware":
            "Malware or Harmful File",

        "privacy":
            "Privacy Violation",

        "fraud":
            "Fraud or Phishing",

        "harassment":
            "Harassment or Threat",

        "illegal_content":
            "Illegal Content",

        "security":
            "Security Incident",

        "other":
            "Other Complaint"

    }

    # ===== COMPLAINT TYPE NAMES END =====


    # ===== FORMAT ABUSE REPORTS START =====

    formatted_reports = []

    for report_record in abuse_records:

        formatted_report = dict(
            report_record
        )

        formatted_report[
            "formatted_complaint_type"
        ] = complaint_type_names.get(
            report_record["complaint_type"],
            report_record["complaint_type"]
        )

        try:

            formatted_report[
                "formatted_created_at"
            ] = datetime.fromisoformat(
                report_record["created_at"]
            ).strftime(
                "%d %b %Y, %I:%M %p"
            )

        except (
            TypeError,
            ValueError
        ):

            formatted_report[
                "formatted_created_at"
            ] = "Unknown"

        formatted_reports.append(
            formatted_report
        )

    # ===== FORMAT ABUSE REPORTS END =====


    return render_template(

        "admin_abuse_reports.html",

        reports=formatted_reports,

        total_reports=total_reports,

        pending_reports=pending_reports,

        investigating_reports=(
            investigating_reports
        ),

        resolved_reports=resolved_reports,

        closed_reports=closed_reports,

        search_query=search_query,

        status_filter=status_filter,

        message=request.args.get(
            "message"
        )

    )

# ============================================================
# ===== ADMIN ABUSE REPORTS ROUTE END =====
# ============================================================
# ============================================================
# ===== ADMIN PRIVACY REQUESTS START =====
# ============================================================

@app.route("/admin/privacy-requests")
def admin_privacy_requests():

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("admin_login")
        )

    search_query = request.args.get(
        "search",
        ""
    ).strip()

    status_filter = request.args.get(
        "status",
        ""
    ).strip().lower()

    allowed_statuses = {
        "pending",
        "identity_check",
        "processing",
        "completed",
        "rejected"
    }

    if status_filter not in allowed_statuses:

        status_filter = ""

    query = """
        SELECT *
        FROM privacy_requests
        WHERE 1 = 1
    """

    parameters = []

    if search_query:

        search_pattern = (
            "%"
            +
            search_query.lower()
            +
            "%"
        )

        query += """
            AND (
                LOWER(request_reference) LIKE ?
                OR LOWER(full_name) LIKE ?
                OR LOWER(email) LIKE ?
                OR LOWER(COALESCE(access_code, '')) LIKE ?
            )
        """

        parameters.extend(
            [
                search_pattern,
                search_pattern,
                search_pattern,
                search_pattern
            ]
        )

    if status_filter:

        query += """
            AND status = ?
        """

        parameters.append(
            status_filter
        )

    query += """
        ORDER BY submitted_at DESC
    """

    connection = None
    privacy_requests = []

    try:

        connection = get_database_connection()

        cursor = connection.execute(
            query,
            tuple(parameters)
        )

        privacy_requests = cursor.fetchall()

    except Exception as error:

        print(
            "Admin privacy request list failed:",
            error
        )

    finally:

        if connection is not None:

            connection.close()

    message = request.args.get(
        "message",
        ""
    ).strip()

    return render_template(
        "admin_privacy_requests.html",

        privacy_requests=privacy_requests,

        search_query=search_query,

        status_filter=status_filter,

        message=message
    )

@app.route("/admin/audit-logs")
def admin_audit_logs():

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("admin_login")
        )

    connection = None
    audit_logs = []

    try:

        connection = get_database_connection()

        cursor = connection.execute(
            """
            SELECT *
            FROM audit_logs
            ORDER BY created_at DESC
            LIMIT 500
            """
        )

        audit_logs = cursor.fetchall()

    except Exception as error:

        print(
            "Audit log list failed:",
            error
        )

    finally:

        if connection is not None:

            connection.close()

    return render_template(
        "admin_audit_logs.html",
        audit_logs=audit_logs
    )


# ============================================================
# ===== ADMIN PRIVACY REQUEST UPDATE START =====
# ============================================================

@app.route(
    "/admin/privacy-requests/<int:request_id>/update",
    methods=["POST"]
)
def admin_update_privacy_request(
    request_id
):

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("admin_login")
        )

    allowed_identity_statuses = {
        "pending",
        "verified",
        "failed"
    }

    allowed_request_statuses = {
        "pending",
        "identity_check",
        "processing",
        "completed",
        "rejected"
    }

    identity_status = request.form.get(
        "identity_status",
        ""
    ).strip().lower()

    request_status = request.form.get(
        "status",
        ""
    ).strip().lower()

    rejection_reason = request.form.get(
        "rejection_reason",
        ""
    ).strip()

    if identity_status not in allowed_identity_statuses:

        return redirect(
            url_for(
                "admin_privacy_requests",
                message=(
                    "Invalid identity status."
                )
            )
        )

    if request_status not in allowed_request_statuses:

        return redirect(
            url_for(
                "admin_privacy_requests",
                message=(
                    "Invalid privacy request status."
                )
            )
        )

    if len(rejection_reason) > 500:

        return redirect(
            url_for(
                "admin_privacy_requests",
                message=(
                    "Rejection reason cannot exceed "
                    "500 characters."
                )
            )
        )

    if (
        request_status == "rejected"
        and
        not rejection_reason
    ):

        return redirect(
            url_for(
                "admin_privacy_requests",
                message=(
                    "A rejection reason is required "
                    "when rejecting a request."
                )
            )
        )

    if request_status != "rejected":

        rejection_reason = None

    updated_at = datetime.now()

    completed_at = None
    retention_until = None

    if request_status in {
        "completed",
        "rejected"
    }:

        completed_at = (
            updated_at.isoformat()
        )

        retention_until = (
            updated_at
            +
            timedelta(
                days=PRIVACY_REQUEST_RETENTION_DAYS
            )
        ).isoformat()

    connection = None

    try:

        connection = get_database_connection()

        connection.execute(
            """
            UPDATE privacy_requests

            SET
                identity_status = ?,
                status = ?,
                rejection_reason = ?,
                completed_at = ?,
                retention_until = ?,
                updated_at = ?

            WHERE id = ?
            """,
            (
                identity_status,
                request_status,
                rejection_reason,
                completed_at,
                retention_until,
                updated_at.isoformat(),
                request_id
            )
        )

        connection.commit()
        create_audit_log(
            event_type="privacy_request_update",
            entity_type="privacy_request",
            entity_id=request_id,
            action="status_updated",
            actor_type="admin",
            actor_identifier=ADMIN_USERNAME,
            event_details=(
                f"Identity status changed to: {identity_status}; "
                f"Request status changed to: {request_status}"
            )
        )

    except Exception as error:

        if connection is not None:

            try:

                connection.rollback()

            except Exception:

                pass

        print(
            "Privacy request update failed:",
            error
        )

        return redirect(
            url_for(
                "admin_privacy_requests",
                message=(
                    "Privacy request could not be updated."
                )
            )
        )

    finally:

        if connection is not None:

            connection.close()

    return redirect(
        url_for(
            "admin_privacy_requests",
            message=(
                "Privacy request updated successfully."
            )
        )
    )

# ============================================================
# ===== ADMIN PRIVACY REQUESTS END =====
# ============================================================

# ============================================================
# ===== ADMIN UPDATE ABUSE STATUS ROUTE START =====
# ============================================================

@app.route(
    "/admin/abuse-reports/<int:report_id>/status",
    methods=["POST"]
)
def admin_update_abuse_status(report_id):

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("admin_login")
        )


    new_status = request.form.get(
        "status",
        ""
    ).strip()


    allowed_statuses = {
        "Pending",
        "Investigating",
        "Resolved",
        "Closed"
    }


    if new_status not in allowed_statuses:

        return redirect(
            url_for(
                "admin_abuse_reports",
                message=(
                    "Invalid complaint status."
                )
            )
        )


    connection = get_database_connection()


    report_record = connection.execute(
        """
        SELECT id
        FROM report_abuse
        WHERE id = ?
        """,
        (report_id,)
    ).fetchone()


    if report_record is None:

        connection.close()

        return redirect(
            url_for(
                "admin_abuse_reports",
                message=(
                    "Abuse report not found."
                )
            )
        )


    updated_at = datetime.now()

    resolved_at = None
    closed_at = None
    retention_until = None

    if new_status == "Resolved":

        resolved_at = updated_at.isoformat()

    elif new_status == "Closed":

        closed_at = updated_at.isoformat()

        retention_until = (
            updated_at
            +
            timedelta(
                days=ABUSE_RETENTION_DAYS
            )
        ).isoformat()

    connection.execute(
        """
        UPDATE report_abuse

        SET
            status = ?,

            resolved_at = CASE
                WHEN ? IS NOT NULL
                THEN ?
                ELSE resolved_at
            END,

            closed_at = CASE
                WHEN ? IS NOT NULL
                THEN ?
                ELSE closed_at
            END,

            retention_until = CASE
                WHEN ? IS NOT NULL
                THEN ?
                ELSE retention_until
            END

        WHERE id = ?
        """,
        (
            new_status,

            resolved_at,
            resolved_at,

            closed_at,
            closed_at,

            retention_until,
            retention_until,

            report_id
        )
    )

    connection.commit()

    create_audit_log(
        event_type="abuse_report_update",
        entity_type="abuse_report",
        entity_id=report_id,
        action="status_updated",
        actor_type="admin",
        actor_identifier=ADMIN_USERNAME,
        event_details=(
            f"Abuse report status changed to: {new_status}"
        )
    )

    connection.close()


    return redirect(
        url_for(
            "admin_abuse_reports",
            message=(
                "Abuse report status updated."
            )
        )
    )

# ============================================================
# ===== ADMIN UPDATE ABUSE STATUS ROUTE END =====
# ============================================================

# ============================================================
# ===== 28. ADMIN LOGOUT ROUTE START =====
# ============================================================

@app.route("/admin-logout")
def admin_logout():

    if session.get("admin_logged_in"):

        create_audit_log(
            event_type="admin_logout",
            entity_type="admin_session",
            entity_id=ADMIN_USERNAME,
            action="logout",
            actor_type="admin",
            actor_identifier=ADMIN_USERNAME,
            event_details=(
                "Administrator logged out."
            )
        )

    session.clear()

    return redirect(
        url_for("admin_login")
    )

# ============================================================
# ===== 28. ADMIN LOGOUT ROUTE END =====
# ============================================================


# ===== 29. FILE UPLOAD ROUTE START =====

@app.route(
    "/upload",
    methods=["POST"]
)
@limiter.limit("10 per hour")
def upload_file():

    if "file" not in request.files:

        return jsonify(
            {
                "success": False,
                "message": (
                    "Please select a file."
                )
            }
        ), 400

    uploaded_file = request.files["file"]

    if uploaded_file.filename == "":

        return jsonify(
            {
                "success": False,
                "message": (
                    "Please select a file."
                )
            }
        ), 400

    if not allowed_file(
        uploaded_file.filename
    ):

        return jsonify(
            {
                "success": False,
                "message": (
                    "This file type is not allowed."
                )
            }
        ), 400

    original_filename = secure_filename(
        uploaded_file.filename
    )
        # ============================================================
    # ===== REAL FILE SIGNATURE CHECK START =====
    # ============================================================

    file_extension = (
        original_filename
        .rsplit(
            ".",
            1
        )[1]
        .lower()
    )

    signature_valid, signature_error = (
        validate_uploaded_file_signature(
            uploaded_file,
            file_extension
        )
    )

    if not signature_valid:

        return jsonify(
            {
                "success": False,
                "message": signature_error
            }
        ), 400

    # File pointer reset rakho taaki save ke waqt
    # complete file correctly save ho.
    uploaded_file.stream.seek(0)

    # ============================================================
    # ===== REAL FILE SIGNATURE CHECK END =====
    # ============================================================
    # ============================================================
# ===== UPLOADED FILENAME VALIDATION START =====
# ============================================================

    if not original_filename:

        return jsonify(
            {
                "success": False,
                "message": (
                "The selected file has an invalid filename."
                )
            }
        ),  400


    if len(original_filename) > 180:

        return jsonify(
        {
            "success": False,
            "message": (
                "The filename is too long. "
                "Use a filename shorter than 180 characters."
            )
        }
    ), 400


    if original_filename.startswith("."):

        return jsonify(
            {
                "success": False,
                "message": (
                "Hidden or invalid filenames are not allowed."
                )
            }
        ), 400

# ============================================================
# ===== UPLOADED FILENAME VALIDATION END =====
# ============================================================

    file_extension = (
        original_filename
        .rsplit(".", 1)[1]
        .lower()
    )

    stored_filename = (
        f"{uuid.uuid4().hex}."
        f"{file_extension}"
    )
    # ============================================================
    # ===== PREPARE FILE FOR SUPABASE STORAGE START =====
    # ============================================================

    uploaded_file.stream.seek(0)

    file_data = uploaded_file.stream.read()

    uploaded_file.stream.seek(0)

    file_size = len(
        file_data
    )

    # ============================================================
    # ===== PREPARE FILE FOR SUPABASE STORAGE END =====
    # ============================================================
    
    # ============================================================
    # ===== EMPTY FILE VALIDATION START =====
    # ============================================================

    if file_size <= 0:

        delete_stored_file(
            stored_filename
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "Empty files cannot be uploaded."
                )
            }
        ), 400

    # ============================================================
    # ===== EMPTY FILE VALIDATION END =====
    # ============================================================

    expiry_minutes = request.form.get(
        "expiry_time",
        "60"
    )

    try:

        expiry_minutes = int(
            expiry_minutes
        )

    except ValueError:

        expiry_minutes = 60

    allowed_expiry_times = {
        10,
        60,
        360,
        1440
    }

    if (
        expiry_minutes
        not in allowed_expiry_times
    ):

        expiry_minutes = 60

        # ============================================================
    # ===== FILE PIN VALIDATION START =====
    # ============================================================

    file_pin = request.form.get(
        "file_pin",
        ""
    ).strip()
        # ============================================================
    # ===== REQUIRED FILE PIN CHECK START =====
    # ============================================================

    if not file_pin:

        delete_stored_file(
            stored_filename
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "A 4-digit security PIN is required."
                )
            }
        ), 400

    # ============================================================
    # ===== REQUIRED FILE PIN CHECK END =====
    # ============================================================

    # PIN optional hai.
    # Agar PIN diya hai to exactly 4 digits hona chahiye.
    if not (
        file_pin.isdigit()
        and
        len(file_pin) == 4
    ):

        delete_stored_file(
            stored_filename
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "PIN must contain exactly 4 digits."
                )
            }
        ), 400

        delete_stored_file(
            stored_filename
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "PIN must contain exactly 4 digits."
                )
            }
        ), 400

    # Easy-to-guess PIN ko reject karo.
    if (
        file_pin
        and
        file_pin in WEAK_FILE_PINS
    ):

        delete_stored_file(
            stored_filename
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "This PIN is too easy to guess. "
                    "Please choose a stronger 4-digit PIN."
                )
            }
        ), 400

    # ============================================================
    # ===== FILE PIN VALIDATION END =====
    # ============================================================


    # ============================================================
    # ===== FILE PIN HASHING START =====
    # ============================================================

    pin_hash = None

    if file_pin:

        pin_hash = generate_password_hash(
            file_pin
        )

    # ============================================================
    # ===== FILE PIN HASHING END =====
    # ============================================================
    # ============================================================
    # ===== TRANSFER MODE VALIDATION START =====
    # ============================================================

    transfer_mode = request.form.get(
        "transfer_mode",
        "download"
    ).strip().lower()

    allowed_transfer_modes = {
        "download",
        "view_print"
    }

    if transfer_mode not in allowed_transfer_modes:

        delete_stored_file(
            stored_filename
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "Please select a valid transfer mode."
                )
            }
        ), 400

    # View + Print mode currently sirf PDF aur images ke liye.
    view_print_extensions = {
        "pdf",
        "jpg",
        "jpeg",
        "png"
    }

    if (
        transfer_mode == "view_print"
        and
        file_extension not in view_print_extensions
    ):

        delete_stored_file(
            stored_filename
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "View + Print mode supports only "
                    "PDF, JPG, JPEG and PNG files."
                )
            }
        ), 400

    # View + Print file direct one-time download nahi hoti.
    if transfer_mode == "view_print":

        one_time_download = 0

    # ============================================================
    # ===== TRANSFER MODE VALIDATION END =====
    # ============================================================
    one_time_value = request.form.get(
        "one_time_download",
        "false"
    )

    one_time_download = (
        1
        if (
            one_time_value == "true"
            and
            transfer_mode == "download"
        )
        else 0
    )

    uploaded_at = datetime.now()

    expires_at = (
        uploaded_at
        +
        timedelta(
            minutes=expiry_minutes
        )
    )
    # ============================================================
    # ===== ACTIVE STORAGE LIMIT CHECK START =====
    # ============================================================

    storage_connection = (
        get_database_connection()
    )

    try:

        active_storage = (
            storage_connection.execute(
                """
                SELECT
                    COALESCE(
                        SUM(file_size),
                        0
                    )
                FROM files
                WHERE status = 'active'
                """
            ).fetchone()[0]
        )

    finally:

        storage_connection.close()


    if (
        active_storage
        +
        file_size
        >
        FYLOQ_STORAGE_LIMIT
    ):

        return jsonify(
            {
                "success": False,
                "message": (
                    "Fyloq storage is currently full. "
                    "Please try again later."
                )
            }
        ), 507

    # ============================================================
    # ===== ACTIVE STORAGE LIMIT CHECK END =====
    # ============================================================


    access_code = generate_access_code()

        # ============================================================
    # ===== APPLICATION-LEVEL FILE ENCRYPTION START =====
    # ============================================================

    try:

        encryption_key_version = int(
            os.getenv(
                "FILE_ENCRYPTION_KEY_VERSION",
                "1"
            )
        )

        encrypted_file = encrypt_file_data(
            file_data=file_data,
            stored_filename=stored_filename,
            encryption_key_version=(
                encryption_key_version
            )
        )

    except Exception as error:

        print(
            "File encryption failed:",
            error
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "File encryption failed. "
                    "Please try again."
                )
            }
        ), 500

    # ============================================================
    # ===== APPLICATION-LEVEL FILE ENCRYPTION END =====
    # ============================================================


    # ============================================================
    # ===== ENCRYPTED SUPABASE STORAGE UPLOAD START =====
    # ============================================================

    encrypted_content_type = (
        "application/octet-stream"
    )

    try:

        upload_file_to_storage(
            stored_filename,
            encrypted_file.encrypted_data,
            encrypted_content_type
        )

    except Exception as error:

        print(
            "Encrypted Storage upload failed:",
            error
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "File upload failed. "
                    "Please try again."
                )
            }
        ), 500

    # ============================================================
    # ===== ENCRYPTED SUPABASE STORAGE UPLOAD END =====
    # ============================================================

    # ============================================================
    # ===== DATABASE RECORD INSERT START =====
    # ============================================================

    connection = None

    try:

        connection = get_database_connection()

        connection.execute(
            """
            INSERT INTO files (

                original_filename,
                stored_filename,
                access_code,
                pin_hash,
                file_size,
                file_extension,
                expiry_minutes,
                uploaded_at,
                expires_at,
                one_time_download,
                download_count,
                status,
                failed_pin_attempts,
                locked_until,
                transfer_mode,
                view_count,
                last_viewed_at,
                print_count,
                last_printed_at,
                encryption_algorithm,
                encryption_version,
                encryption_key_version,
                file_nonce,
                wrapped_data_key,
                key_wrap_nonce,
                encrypted_size

            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                original_filename,
                stored_filename,
                access_code,
                pin_hash,
                file_size,
                file_extension,
                expiry_minutes,
                uploaded_at.isoformat(),
                expires_at.isoformat(),
                one_time_download,
                0,
                "active",
                0,
                None,
                transfer_mode,
                0,
                None,
                0,
                None,
                encrypted_file.encryption_algorithm,
                encrypted_file.encryption_version,
                encrypted_file.encryption_key_version,
                encrypted_file.file_nonce,
                encrypted_file.wrapped_data_key,
                encrypted_file.key_wrap_nonce,
                encrypted_file.encrypted_size
            )
        )

        connection.commit()

    except Exception as error:

        if connection is not None:

            try:

                connection.rollback()

            except Exception:

                pass

        # DB record create nahi hua,
        # isliye Supabase Storage file rollback/delete karo.
        try:

            delete_file_from_storage(
                stored_filename
            )

        except Exception as cleanup_error:

            print(
                "Storage rollback failed:",
                cleanup_error
            )

        print(
            "Database insert failed:",
            error
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "File upload could not be completed. "
                    "Please try again."
                )
            }
        ), 500

    finally:

        if connection is not None:

            connection.close()

    # ============================================================
    # ===== DATABASE RECORD INSERT END =====
    # ============================================================

    access_url = (
        request.url_root.rstrip("/")
        +
        "/?code="
        +
        access_code
    )

    qr_code_data = generate_qr_code_data(
        access_url
    )

    return jsonify(
        {
            "success": True,

            "message": (
                "File uploaded successfully."
            ),

            "access_code": access_code,

            "pin_required": bool(
                file_pin
            ),

            "filename": original_filename,

            "file_size": file_size,

            "expiry_minutes": expiry_minutes,

            "expires_at": expires_at.strftime(
                "%d %b %Y, %I:%M %p"
            ),

            "expires_at_iso": (
                expires_at.astimezone().isoformat()
            ),

                       "one_time_download": bool(
                one_time_download
            ),

            "transfer_mode": transfer_mode,

            "transfer_mode_label": (
                "View + Print"
                if transfer_mode == "view_print"
                else "Download"
            ),

            "access_url": access_url,

            "qr_code": qr_code_data
        }
    )

# ===== 29. FILE UPLOAD ROUTE END =====


# ===== 30. ACCESS FILE VERIFICATION ROUTE START =====

@app.route(
    "/access-file",
    methods=["POST"]
)
@limiter.limit("20 per minute")
def access_file():

    request_data = request.get_json(
        silent=True
    ) or {}

    access_code = str(
        request_data.get(
            "access_code",
            ""
        )
    ).strip()

    file_pin = str(
        request_data.get(
            "pin",
            ""
        )
    ).strip()

    if not (
        access_code.isdigit()
        and
        len(access_code) == 6
    ):

        return jsonify(
            {
                "success": False,
                "message": (
                    "Enter a valid "
                    "6-digit access code."
                )
            }
        ), 400

    connection = get_database_connection()

    file_record = connection.execute(
        """
        SELECT *
        FROM files
        WHERE access_code = ?
        """,
        (access_code,)
    ).fetchone()

    connection.close()

    if file_record is None:

        return jsonify(
            {
                "success": False,
                "message": (
                    "No file was found with "
                    "this access code."
                )
            }
        ), 404

    if file_record["status"] != "active":

        return jsonify(
            {
                "success": False,
                "message": (
                    "This file is no longer "
                    "available."
                )
            }
        ), 410

    if is_file_expired(
        file_record
    ):

        mark_file_expired(
            file_record
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "This file has expired "
                    "and was deleted."
                )
            }
        ), 410

    stored_file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file_record["stored_filename"]
    )

    
    lock_remaining_seconds = (
        get_pin_lock_remaining_seconds(
            file_record
        )
    )

    if lock_remaining_seconds > 0:

        lock_minutes = max(
            1,
            (
                lock_remaining_seconds + 59
            ) // 60
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "Too many incorrect PIN "
                    "attempts. Try again after "
                    f"{lock_minutes} minute(s)."
                )
            }
        ), 429

    if file_record["pin_hash"]:

        if not file_pin:

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "This file requires "
                        "a 4-digit PIN."
                    )
                }
            ), 401

        if not check_password_hash(
            file_record["pin_hash"],
            file_pin
        ):

            attempts = register_wrong_pin(
                file_record
            )

            attempts_left = (
                MAX_PIN_ATTEMPTS
                -
                attempts
            )

            if attempts_left <= 0:

                return jsonify(
                    {
                        "success": False,
                        "message": (
                            "Too many incorrect "
                            "PIN attempts. Access "
                            "is locked for "
                            f"{PIN_LOCK_MINUTES} "
                            "minutes."
                        )
                    }
                ), 429

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "Incorrect PIN. "
                        f"{attempts_left} "
                        "attempt(s) remaining."
                    )
                }
            ), 401

        reset_pin_security(
            file_record["id"]
        )

        # ============================================================
    # ===== VERIFIED FILE ACTION START =====
    # ============================================================

    transfer_mode = (
        file_record["transfer_mode"]
        or
        "download"
    )

    if transfer_mode == "view_print":

        access_token = (
            download_token_serializer.dumps(
                {
                    "access_code": access_code
                },
                salt="quickvault-view-print"
            )
        )

        action_url = url_for(
            "view_print_page",
            access_code=access_code,
            token=access_token
        )

        action_label = (
            "View + Print"
        )

    else:

        access_token = (
            download_token_serializer.dumps(
                {
                    "access_code": access_code
                },
                salt="quickvault-download"
            )
        )

        action_url = url_for(
            "download_file",
            access_code=access_code,
            token=access_token
        )

        action_label = (
            "Download File"
        )

    # ============================================================
    # ===== VERIFIED FILE ACTION END =====
    # ============================================================

    return jsonify(
        {
            "success": True,

            "message": (
                "Access code and PIN "
                "verified successfully."
            ),

            "filename": (
                file_record[
                    "original_filename"
                ]
            ),

            "file_size": (
                file_record["file_size"]
            ),

            "expires_at": (
                file_record["expires_at"]
            ),

            "one_time_download": bool(
                file_record[
                    "one_time_download"
                ]
            ),

            "transfer_mode": transfer_mode,

            "action_label": action_label,

            "action_url": action_url,

            # Existing JavaScript compatibility.
            "download_url": action_url
        }
    )

# ===== 30. ACCESS FILE VERIFICATION ROUTE END =====
# ============================================================
# ===== LIVE FILE TRACKING ROUTE START =====
# ============================================================

@app.route(
    "/track-file",
    methods=["POST"]
)
@limiter.limit("30 per minute")
def track_file():

    request_data = request.get_json(
        silent=True
    ) or {}

    access_code = str(
        request_data.get(
            "access_code",
            ""
        )
    ).strip()

    # ===== ACCESS CODE VALIDATION =====

    if not (
        access_code.isdigit()
        and
        len(access_code) == 6
    ):

        return jsonify(
            {
                "success": False,
                "message": "Enter a valid 6-digit access code."
            }
        ), 400

    connection = get_database_connection()

    file_record = connection.execute(
        """
        SELECT *
        FROM files
        WHERE access_code = ?
        """,
        (
            access_code,
        )
    ).fetchone()

    connection.close()

    if file_record is None:

        return jsonify(
            {
                "success": False,
                "message": "No tracking information found for this access code."
            }
        ), 404


    # ===== FILE STATUS CHECK =====

    current_status = (
        file_record["status"]
        or
        "active"
    )

    expires_at = datetime.fromisoformat(
        file_record["expires_at"]
    )

    current_time = datetime.now()

    remaining_seconds = max(
        0,
        int(
            (
                expires_at
                -
                current_time
            ).total_seconds()
        )
    )

    if (
        current_time >= expires_at
        and
        current_status == "active"
    ):

        current_status = "expired"


    # ===== LAST ACTIVITY =====

    activity_times = []

    if file_record["uploaded_at"]:

        activity_times.append(
            file_record["uploaded_at"]
        )

    if file_record["last_viewed_at"]:

        activity_times.append(
            file_record["last_viewed_at"]
        )

    if file_record["last_printed_at"]:

        activity_times.append(
            file_record["last_printed_at"]
        )

    last_activity = (
        max(activity_times)
        if activity_times
        else None
    )


    return jsonify(
        {
            "success": True,

            "status": current_status,

            "filename": file_record[
                "original_filename"
            ],

            "file_size": file_record[
                "file_size"
            ],

            "transfer_mode": (
                file_record[
                    "transfer_mode"
                ]
                or
                "download"
            ),

            "uploaded_at": file_record[
                "uploaded_at"
            ],

            "expires_at": file_record[
                "expires_at"
            ],

            "remaining_seconds": (
                remaining_seconds
            ),

            "download_count": (
                file_record[
                    "download_count"
                ]
                or 0
            ),

            "view_count": (
                file_record[
                    "view_count"
                ]
                or 0
            ),

            "print_count": (
                file_record[
                    "print_count"
                ]
                or 0
            ),

            "last_viewed_at": (
                file_record[
                    "last_viewed_at"
                ]
            ),

            "last_printed_at": (
                file_record[
                    "last_printed_at"
                ]
            ),

            "last_activity": (
                last_activity
            ),

            "one_time_download": bool(
                file_record[
                    "one_time_download"
                ]
            )
        }
    )

# ============================================================
# ===== LIVE FILE TRACKING ROUTE END =====
# ============================================================

# ============================================================
# ===== VIEW + PRINT PAGE ROUTE START =====
# ============================================================

@app.route(
    "/view-print/<access_code>",
    methods=["GET"]
)
def view_print_page(access_code):

    access_token = request.args.get(
        "token",
        ""
    )

    if not access_token:

        return (
            "Invalid View + Print request.",
            403
        )

    try:

        token_data = (
            download_token_serializer.loads(
                access_token,
                salt="quickvault-view-print",
                max_age=300
            )
        )

    except SignatureExpired:

        return (
            "View + Print link expired. "
            "Enter the access code and PIN again.",
            403
        )

    except BadSignature:

        return (
            "Invalid View + Print link.",
            403
        )

    if (
        token_data.get("access_code")
        !=
        access_code
    ):

        return (
            "Invalid access code.",
            403
        )

    connection = get_database_connection()

    file_record = connection.execute(
        """
        SELECT *
        FROM files
        WHERE access_code = ?
        """,
        (
            access_code,
        )
    ).fetchone()

    connection.close()

    if file_record is None:

        return (
            "File not found.",
            404
        )

    if (
        file_record["transfer_mode"]
        !=
        "view_print"
    ):

        return (
            "This file is not available in View + Print mode.",
            403
        )

    if file_record["status"] != "active":

        return (
            "This file is no longer available.",
            410
        )

    if is_file_expired(
        file_record
    ):

        mark_file_expired(
            file_record
        )

        return (
            "This file has expired.",
            410
        )

    

    file_type = (
        file_record["file_extension"]
        .lower()
    )

    if file_type not in {
        "pdf",
        "jpg",
        "jpeg",
        "png"
    }:

        return (
            "This file type cannot be displayed.",
            415
        )

    connection = get_database_connection()

    connection.execute(
        """
        UPDATE files
        SET
            view_count = view_count + 1,
            last_viewed_at = ?
        WHERE id = ?
        """,
        (
            datetime.now().isoformat(),
            file_record["id"]
        )
    )

    connection.commit()

    connection.close()

    content_url = url_for(
        "view_print_content",
        access_code=access_code,
        token=access_token
    )

    try:

        formatted_expiry = (
            datetime.fromisoformat(
                file_record["expires_at"]
            ).strftime(
                "%d %b %Y, %I:%M %p"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        formatted_expiry = (
            file_record["expires_at"]
        )

    return render_template(
        "view_print.html",

        filename=(
            file_record[
                "original_filename"
            ]
        ),

        file_type=file_type,

        content_url=content_url,

        expires_at=formatted_expiry
    )

# ============================================================
# ===== VIEW + PRINT PAGE ROUTE END =====
# ============================================================


# ============================================================
# ===== VIEW + PRINT CONTENT ROUTE START =====
# ============================================================

@app.route(
    "/view-print-content/<access_code>",
    methods=["GET"]
)
def view_print_content(access_code):

    access_token = request.args.get(
        "token",
        ""
    )

    if not access_token:

        return (
            "Invalid file request.",
            403
        )

    try:

        token_data = (
            download_token_serializer.loads(
                access_token,
                salt="quickvault-view-print",
                max_age=300
            )
        )

    except SignatureExpired:

        return (
            "Secure file link expired.",
            403
        )

    except BadSignature:

        return (
            "Invalid secure file link.",
            403
        )

    if (
        token_data.get("access_code")
        !=
        access_code
    ):

        return (
            "Invalid access code.",
            403
        )

    connection = get_database_connection()

    file_record = connection.execute(
        """
        SELECT *
        FROM files
        WHERE access_code = ?
        """,
        (
            access_code,
        )
    ).fetchone()

    connection.close()

    if file_record is None:

        return (
            "File not found.",
            404
        )

    if (
        file_record["transfer_mode"]
        !=
        "view_print"
    ):

        return (
            "Direct file access is not allowed.",
            403
        )

    if file_record["status"] != "active":

        return (
            "This file is no longer available.",
            410
        )

    if is_file_expired(
        file_record
    ):

        mark_file_expired(
            file_record
        )

        return (
            "This file has expired.",
            410
        )

        # ============================================================
    # ===== SUPABASE VIEW FILE FETCH START =====
    # ============================================================

    try:

        file_data = download_file_from_storage(
            file_record["stored_filename"]
        )

    except Exception as error:

        print(
            "Supabase View + Print fetch failed:",
            error
        )

        error_text = str(
            error
        ).lower()

        if (
            "404" in error_text
            or
            "not found" in error_text
        ):

            mark_file_missing(
                file_record["id"]
            )

            return (
                "Stored file not found.",
                404
            )

        return (
            "File is temporarily unavailable.",
            503
        )

    # ============================================================
    # ===== SUPABASE VIEW FILE FETCH END =====
    # ============================================================
    # ============================================================
    # ===== VIEW + PRINT FILE DECRYPTION START =====
    # ============================================================

    try:

        file_data = decrypt_file_data(
            encrypted_data=file_data,

            stored_filename=(
                file_record["stored_filename"]
            ),

            file_nonce=(
                file_record["file_nonce"]
            ),

            wrapped_data_key=(
                file_record["wrapped_data_key"]
            ),

            key_wrap_nonce=(
                file_record["key_wrap_nonce"]
            )
        )

    except Exception as error:

        print(
            "View + Print file decryption failed:",
            error
        )

        return (
            "File security verification failed. "
            "The file cannot be displayed.",
            500
        )

    # ============================================================
    # ===== VIEW + PRINT FILE DECRYPTION END =====
    # ============================================================
    file_extension = (
        file_record["file_extension"]
        .lower()
    )

    mime_types = {

        "pdf": "application/pdf",

        "jpg": "image/jpeg",

        "jpeg": "image/jpeg",

        "png": "image/png"
    }

    file_mime_type = mime_types.get(
        file_extension
    )

    if file_mime_type is None:

        return (
            "Unsupported viewer file type.",
            415
        )

    response = send_file(
        BytesIO(file_data),

        mimetype=file_mime_type,

        as_attachment=False,

        download_name=(
            file_record[
                "original_filename"
            ]
        ),

        conditional=True
    )

    response.headers[
        "Content-Disposition"
    ] = (
        "inline; filename=\""
        +
        file_record[
            "original_filename"
        ].replace(
            "\"",
            ""
        )
        +
        "\""
    )

    response.headers[
        "Cache-Control"
    ] = (
        "no-store, no-cache, "
        "must-revalidate, private"
    )

    response.headers[
        "Pragma"
    ] = "no-cache"

    response.headers[
        "X-Frame-Options"
    ] = "SAMEORIGIN"

    return response

# ============================================================
# ===== VIEW + PRINT CONTENT ROUTE END =====
# ============================================================

# ===== 31. ACTUAL FILE DOWNLOAD ROUTE START =====

@app.route(
    "/download/<access_code>",
    methods=["GET"]
)
def download_file(access_code):

    # ============================================================
    # ===== SECURE DOWNLOAD TOKEN VALIDATION START =====
    # ============================================================

    download_token = request.args.get(
        "token",
        ""
    )

    if not download_token:

        return (
            "Invalid download request.",
            403
        )

    try:

        token_data = (
            download_token_serializer.loads(
                download_token,
                salt="quickvault-download",
                max_age=300
            )
        )

    except SignatureExpired:

        return (
            "Download link expired. "
            "Enter the access code again.",
            403
        )

    except BadSignature:

        return (
            "Invalid download link.",
            403
        )

    if (
        token_data.get("access_code")
        != access_code
    ):

        return (
            "Invalid access code.",
            403
        )

    # ============================================================
    # ===== SECURE DOWNLOAD TOKEN VALIDATION END =====
    # ============================================================


    # ============================================================
    # ===== GET FILE RECORD START =====
    # ============================================================

    connection = get_database_connection()

    file_record = connection.execute(
        """
        SELECT *
        FROM files
        WHERE access_code = ?
        """,
        (access_code,)
    ).fetchone()

    connection.close()

    if file_record is None:

        return (
            "File not found.",
            404
        )

    if file_record["status"] != "active":

        return (
            "This file is no longer available.",
            410
        )

    # ============================================================
    # ===== GET FILE RECORD END =====
    # ============================================================


    # ============================================================
    # ===== EXPIRY CHECK START =====
    # ============================================================

    if is_file_expired(
        file_record
    ):

        mark_file_expired(
            file_record
        )

        return (
            "This file has expired.",
            410
        )

    # ============================================================
    # ===== EXPIRY CHECK END =====
    # ============================================================


    # ============================================================
    # ===== SUPABASE PRIVATE STORAGE DOWNLOAD START =====
    # ============================================================

    try:

        file_data = (
            download_file_from_storage(
                file_record[
                    "stored_filename"
                ]
            )
        )

    except Exception as error:

        print(
            "Supabase Storage download failed:",
            error
        )

        error_text = str(
            error
        ).lower()

        if (
            "404" in error_text
            or
            "not found" in error_text
        ):

            mark_file_missing(
                file_record["id"]
            )

            return (
                "Stored file not found.",
                404
            )

        return (
            "File is temporarily unavailable. "
            "Please try again.",
            503
        )

    # ============================================================
    # ===== SUPABASE PRIVATE STORAGE DOWNLOAD END =====
    # ============================================================

    # ============================================================
    # ===== APPLICATION-LEVEL FILE DECRYPTION START =====
    # ============================================================

    try:

        file_data = decrypt_file_data(
            encrypted_data=file_data,

            stored_filename=(
                file_record["stored_filename"]
            ),

            file_nonce=(
                file_record["file_nonce"]
            ),

            wrapped_data_key=(
                file_record["wrapped_data_key"]
            ),

            key_wrap_nonce=(
                file_record["key_wrap_nonce"]
            )
        )

    except Exception as error:

        print(
            "File decryption failed:",
            error
        )

        return (
            "File security verification failed. "
            "The file cannot be downloaded.",
            500
        )

    # ============================================================
    # ===== APPLICATION-LEVEL FILE DECRYPTION END =====
    # ============================================================
    # ============================================================
    # ===== DOWNLOAD DATABASE UPDATE START =====
    # ============================================================

    connection = get_database_connection()

    try:

        if file_record[
            "one_time_download"
        ]:

            # One-time file ko Supabase Storage
            # se permanently delete karo.
            delete_file_from_storage(
                file_record[
                    "stored_filename"
                ]
            )

            # Existing Fyloq one-time logic preserve:
            # file record bhi permanently remove hoga.
            connection.execute(
                """
                DELETE FROM files
                WHERE id = ?
                """,
                (
                    file_record["id"],
                )
            )

        else:

            connection.execute(
                """
                UPDATE files
                SET download_count =
                    download_count + 1
                WHERE id = ?
                """,
                (
                    file_record["id"],
                )
            )

        connection.commit()

    except Exception as error:

        try:

            connection.rollback()

        except Exception:

            pass

        print(
            "Download database update failed:",
            error
        )

        return (
            "Download could not be completed. "
            "Please try again.",
            500
        )

    finally:

        connection.close()

    # ============================================================
    # ===== DOWNLOAD DATABASE UPDATE END =====
    # ============================================================


    # ============================================================
    # ===== SEND FILE TO USER START =====
    # ============================================================

    return send_file(
        BytesIO(
            file_data
        ),

        as_attachment=True,

        download_name=file_record[
            "original_filename"
        ],

        mimetype=(
            "application/octet-stream"
        )
    )

    # ============================================================
    # ===== SEND FILE TO USER END =====
    # ============================================================

# ===== 31. ACTUAL FILE DOWNLOAD ROUTE END =====

# ===== 32. MANUAL CLEANUP ROUTE START =====

@app.route(
    "/cleanup-expired-files",
    methods=["POST"]
)
def manual_cleanup_expired_files():

    deleted_count = cleanup_expired_files()

    return jsonify(
        {
            "success": True,

            "message": (
                f"{deleted_count} expired "
                "file(s) deleted."
            ),

            "deleted_count": deleted_count
        }
    )

# ===== 32. MANUAL CLEANUP ROUTE END =====

# ============================================================
# ===== RATE LIMIT ERROR START =====
# ============================================================

@app.errorhandler(429)
def rate_limit_error(error):

    if request.path in {
        "/upload",
        "/access-file"
    }:

        return jsonify(
            {
                "success": False,
                "message": (
                    "Too many requests. "
                    "Please wait and try again."
                )
            }
        ), 429

    return (
        "Too many requests. Please wait and try again.",
        429
    )

# ============================================================
# ===== RATE LIMIT ERROR END =====
# ============================================================

# ============================================================
# ===== 404 ERROR HANDLER START =====
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "404.html"
    ), 404

# ============================================================
# ===== 404 ERROR HANDLER END =====
# ============================================================

# ============================================================
# ===== 500 ERROR HANDLER START =====
# ============================================================

@app.errorhandler(500)
def internal_server_error(error):

    return render_template(
        "500.html"
    ), 500

# ============================================================
# ===== 500 ERROR HANDLER END =====
# ============================================================

# ===== 33. FILE TOO LARGE ERROR START =====

@app.errorhandler(413)
def file_too_large(error):

    return jsonify(
        {
            "success": False,

            "message": (
                "Maximum file size is 10 MB."
            )
        }
    ), 413

# ===== 33. FILE TOO LARGE ERROR END =====


# ============================================================
# ===== 34. APPLICATION INITIALIZATION START =====
# ============================================================

# SQLite backup/local mode me hi SQLite-specific
# table creation aur PRAGMA migrations run hongi.
#
# Supabase PostgreSQL schema already SQL Editor
# se safely create kiya gaya hai.

if is_sqlite_database():

    create_database()

    migrate_database()

    create_support_requests_table()


# Existing expiry cleanup logic preserve rahega.
cleanup_expired_files()

# ============================================================
# ===== 34. APPLICATION INITIALIZATION END =====
# ============================================================
# ============================================================
# ===== SITEMAP ROUTE START =====
# ============================================================

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("static", "sitemap.xml")

# ============================================================
# ===== SITEMAP ROUTE END =====
# ============================================================
# ============================================================
# ===== ROBOTS.TXT ROUTE START =====
# ============================================================

@app.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")

# ============================================================
# ===== ROBOTS.TXT ROUTE END =====
# ============================================================
# ============================================================
# ===== LOCAL DEVELOPMENT SERVER START =====
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=not IS_PRODUCTION,
        host="127.0.0.1",
        port=5000
    )

# ============================================================
# ===== LOCAL DEVELOPMENT SERVER END =====
# ============================================================