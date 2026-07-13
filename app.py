# ============================================================
# QUICKVAULT BACKEND
# File: app.py
# ============================================================


# ===== 01. IMPORTS START =====

import base64
import os
import random
import sqlite3
import time
import uuid

from datetime import datetime, timedelta
from io import BytesIO

import qrcode

from dotenv import load_dotenv

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for
)

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

ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME",
    "admin"
)

ADMIN_PASSWORD = os.getenv(
    "ADMIN_PASSWORD",
    ""
)

# ===== 02. ENVIRONMENT VARIABLES END =====


# ===== 03. FLASK APP CONFIGURATION START =====

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY",
    "quickvault-development-secret"
)

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


# ===== 04. SECURITY SETTINGS START =====

MAX_PIN_ATTEMPTS = 5

PIN_LOCK_MINUTES = 10

CLEANUP_INTERVAL_SECONDS = 60

last_cleanup_timestamp = 0

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


# ===== 07. DATABASE CONNECTION START =====

def get_database_connection():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection

# ===== 07. DATABASE CONNECTION END =====


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

            locked_until TEXT

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

        access_code = str(
            random.randint(
                100000,
                999999
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

    delete_stored_file(
        file_record["stored_filename"]
    )

    connection = get_database_connection()

    connection.execute(
        """
        UPDATE files
        SET status = 'expired'
        WHERE id = ?
        """,
        (file_record["id"],)
    )

    connection.commit()

    connection.close()

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

    active_files = connection.execute(
        """
        SELECT *
        FROM files
        WHERE status = 'active'
        """
    ).fetchall()

    deleted_count = 0

    for file_record in active_files:

        if is_file_expired(file_record):

            delete_stored_file(
                file_record["stored_filename"]
            )

            connection.execute(
                """
                UPDATE files
                SET status = 'expired'
                WHERE id = ?
                """,
                (file_record["id"],)
            )

            deleted_count += 1

    connection.commit()

    connection.close()

    return deleted_count

# ===== 17. AUTOMATIC EXPIRED FILE CLEANUP END =====


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


# ===== 23. HOME ROUTE START =====

@app.route("/")
def home():

    return render_template(
        "index.html"
    )

# ===== 23. HOME ROUTE END =====


# ============================================================
# ===== 24. ADMIN LOGIN ROUTE START =====
# ============================================================

@app.route(
    "/admin-login",
    methods=["GET", "POST"]
)
def admin_login():

    if session.get("admin_logged_in"):

        return redirect(
            url_for("admin_dashboard")
        )

    error = None

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            username == ADMIN_USERNAME
            and
            password == ADMIN_PASSWORD
        ):

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin_dashboard")
            )

        error = (
            "Incorrect admin username or password."
        )

    return render_template(
        "admin_login.html",
        error=error
    )

# ============================================================
# ===== 24. ADMIN LOGIN ROUTE END =====
# ============================================================


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

    connection.close()

    # ===== STORAGE PERCENTAGE START =====

    storage_limit = (
        500 * 1024 * 1024
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

    deleted_count = cleanup_expired_files()

    return redirect(
        url_for(
            "admin_dashboard",
            message=(
                f"{deleted_count} expired file(s) cleaned."
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

    connection = get_database_connection()

    file_record = connection.execute(
        """
        SELECT *
        FROM files
        WHERE id = ?
        """,
        (file_id,)
    ).fetchone()

    if file_record is None:

        connection.close()

        return redirect(
            url_for(
                "admin_dashboard",
                message=(
                    "File record not found."
                )
            )
        )

    delete_stored_file(
        file_record["stored_filename"]
    )

    connection.execute(
        """
        DELETE FROM files
        WHERE id = ?
        """,
        (file_id,)
    )

    connection.commit()

    connection.close()

    return redirect(
        url_for(
            "admin_dashboard",
            message=(
                "File deleted successfully."
            )
        )
    )

# ============================================================
# ===== 27. ADMIN DELETE FILE ROUTE END =====
# ============================================================


# ============================================================
# ===== 28. ADMIN LOGOUT ROUTE START =====
# ============================================================

@app.route("/admin-logout")
def admin_logout():

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

    file_extension = (
        original_filename
        .rsplit(".", 1)[1]
        .lower()
    )

    stored_filename = (
        f"{uuid.uuid4().hex}."
        f"{file_extension}"
    )

    stored_file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        stored_filename
    )

    uploaded_file.save(
        stored_file_path
    )

    file_size = os.path.getsize(
        stored_file_path
    )

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

    file_pin = request.form.get(
        "file_pin",
        ""
    ).strip()

    if (
        file_pin
        and
        not (
            file_pin.isdigit()
            and
            len(file_pin) == 4
        )
    ):

        delete_stored_file(
            stored_filename
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "PIN must contain "
                    "exactly 4 digits."
                )
            }
        ), 400

    pin_hash = None

    if file_pin:

        pin_hash = generate_password_hash(
            file_pin
        )

    one_time_value = request.form.get(
        "one_time_download",
        "false"
    )

    one_time_download = (
        1
        if one_time_value == "true"
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

    access_code = generate_access_code()

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
            locked_until

        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            None
        )
    )

    connection.commit()

    connection.close()

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
                expires_at.isoformat()
            ),

            "one_time_download": bool(
                one_time_download
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

    if not os.path.exists(
        stored_file_path
    ):

        mark_file_missing(
            file_record["id"]
        )

        return jsonify(
            {
                "success": False,
                "message": (
                    "The stored file could "
                    "not be found."
                )
            }
        ), 404

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

    download_token = (
        download_token_serializer.dumps(
            {
                "access_code": access_code
            },
            salt="quickvault-download"
        )
    )

    return jsonify(
        {
            "success": True,

            "message": (
                "File verified successfully."
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

            "download_url": (
                f"/download/{access_code}"
                f"?token={download_token}"
            )
        }
    )

# ===== 30. ACCESS FILE VERIFICATION ROUTE END =====


# ===== 31. ACTUAL FILE DOWNLOAD ROUTE START =====

@app.route(
    "/download/<access_code>",
    methods=["GET"]
)
def download_file(access_code):

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

    stored_file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file_record["stored_filename"]
    )

    if not os.path.exists(
        stored_file_path
    ):

        mark_file_missing(
            file_record["id"]
        )

        return (
            "Stored file not found.",
            404
        )

    with open(
        stored_file_path,
        "rb"
    ) as stored_file:

        file_data = stored_file.read()

    connection = get_database_connection()

    if file_record["one_time_download"]:

        connection.execute(
            """
            UPDATE files
            SET
                download_count =
                    download_count + 1,
                status = 'downloaded'
            WHERE id = ?
            """,
            (file_record["id"],)
        )

        delete_stored_file(
            file_record["stored_filename"]
        )

    else:

        connection.execute(
            """
            UPDATE files
            SET download_count =
                download_count + 1
            WHERE id = ?
            """,
            (file_record["id"],)
        )

    connection.commit()

    connection.close()

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


# ===== 34. APPLICATION START =====

if __name__ == "__main__":

    create_database()

    migrate_database()

    cleanup_expired_files()

    app.run(
        debug=True
    )

# ===== 34. APPLICATION END =====