# ============================================================
# FYLOQ SUPABASE CONNECTION TEST
# File: test_supabase.py
# ============================================================

import os

import psycopg2
from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

SUPABASE_DB_URL = os.getenv(
    "SUPABASE_DB_URL"
)

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_SECRET_KEY = os.getenv(
    "SUPABASE_SECRET_KEY"
)

SUPABASE_STORAGE_BUCKET = os.getenv(
    "SUPABASE_STORAGE_BUCKET",
    "fyloq-files"
)


# ============================================================
# DATABASE CONNECTION TEST
# ============================================================

def test_database():

    print("\nTesting Supabase PostgreSQL...")

    connection = psycopg2.connect(
        SUPABASE_DB_URL
    )

    cursor = connection.cursor()

    cursor.execute(
        "SELECT 1;"
    )

    result = cursor.fetchone()

    print(
        "Database connection successful:",
        result
    )

    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN (
            'files',
            'support_requests',
            'report_abuse'
        )
        ORDER BY table_name;
        """
    )

    tables = cursor.fetchall()

    print(
        "Fyloq tables found:"
    )

    for table in tables:

        print(
            "-",
            table[0]
        )

    cursor.close()

    connection.close()


# ============================================================
# SUPABASE STORAGE CONNECTION TEST
# ============================================================

def test_storage():

    print(
        "\nTesting Supabase Storage..."
    )

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_SECRET_KEY
    )

    buckets = (
        supabase
        .storage
        .list_buckets()
    )

    bucket_found = False

    for bucket in buckets:

        bucket_name = getattr(
            bucket,
            "name",
            None
        )

        if (
            bucket_name
            ==
            SUPABASE_STORAGE_BUCKET
        ):

            bucket_found = True

            break

    if bucket_found:

        print(
            "Storage connection successful."
        )

        print(
            "Private bucket found:",
            SUPABASE_STORAGE_BUCKET
        )

    else:

        print(
            "Storage connected, but bucket was not found."
        )


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    try:

        test_database()

        test_storage()

        print(
            "\n✅ SUPABASE TEST COMPLETED SUCCESSFULLY"
        )

    except Exception as error:

        print(
            "\n❌ SUPABASE TEST FAILED"
        )

        print(
            "Error:",
            error
        )