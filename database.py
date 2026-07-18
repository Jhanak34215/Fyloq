# ============================================================
# FYLOQ DATABASE CONFIGURATION
# File: database.py
# ============================================================

import os
import re
import sqlite3

from collections.abc import Mapping
from datetime import date, datetime

import psycopg2
from dotenv import load_dotenv


# ============================================================
# ===== ENVIRONMENT START =====
# ============================================================

load_dotenv()

# ============================================================
# ===== ENVIRONMENT END =====
# ============================================================


# ============================================================
# ===== DATABASE CONFIGURATION START =====
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


# Priority:
#
# 1. Supabase PostgreSQL
# 2. Existing DATABASE_URL backup
# 3. Local SQLite backup

DATABASE_URL = (
    os.getenv(
        "SUPABASE_DB_URL",
        ""
    ).strip()
    or
    os.getenv(
        "DATABASE_URL",
        ""
    ).strip()
    or
    DEFAULT_DATABASE_URL
)


if DATABASE_URL.startswith(
    "postgresql+psycopg2://"
):

    DATABASE_URL = DATABASE_URL.replace(
        "postgresql+psycopg2://",
        "postgresql://",
        1
    )


if DATABASE_URL.startswith(
    "postgres://"
):

    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


IS_SQLITE = DATABASE_URL.startswith(
    "sqlite"
)

# ============================================================
# ===== DATABASE CONFIGURATION END =====
# ============================================================


# ============================================================
# ===== COMPATIBLE DATABASE ROW START =====
# ============================================================

class CompatibleRow(Mapping):

    def __init__(
        self,
        columns,
        values
    ):

        self._columns = list(
            columns
        )

        self._values = [
            self._convert_value(
                value
            )
            for value in values
        ]

        self._data = dict(
            zip(
                self._columns,
                self._values
            )
        )


    @staticmethod
    def _convert_value(
        value
    ):

        # PostgreSQL TIMESTAMPTZ values ko
        # existing Fyloq code-compatible ISO string me convert karo.

        if isinstance(
            value,
            datetime
        ):

            if value.tzinfo is not None:

                value = (
                    value
                    .astimezone()
                    .replace(
                        tzinfo=None
                    )
                )

            return value.isoformat()


        if isinstance(
            value,
            date
        ):

            return value.isoformat()


        return value


    def __getitem__(
        self,
        key
    ):

        # Existing Fyloq dono formats use karta hai:
        #
        # row["status"]
        #
        # row[0]

        if isinstance(
            key,
            int
        ):

            return self._values[
                key
            ]

        return self._data[
            key
        ]


    def __iter__(
        self
    ):

        return iter(
            self._data
        )


    def __len__(
        self
    ):

        return len(
            self._data
        )


    def keys(
        self
    ):

        return self._data.keys()

# ============================================================
# ===== COMPATIBLE DATABASE ROW END =====
# ============================================================


# ============================================================
# ===== POSTGRES CURSOR WRAPPER START =====
# ============================================================

class PostgreSQLCursorWrapper:

    def __init__(
        self,
        cursor,
        connection
    ):

        self.cursor = cursor

        self.connection = (
            connection
        )


    def _columns(
        self
    ):

        if not self.cursor.description:

            return []

        return [
            column.name
            for column
            in self.cursor.description
        ]


    def fetchone(
        self
    ):

        row = self.cursor.fetchone()

        if row is None:

            return None

        return CompatibleRow(
            self._columns(),
            row
        )


    def fetchall(
        self
    ):

        rows = self.cursor.fetchall()

        columns = self._columns()

        return [
            CompatibleRow(
                columns,
                row
            )
            for row in rows
        ]


    @property
    def lastrowid(
        self
    ):

        # SQLite cursor.lastrowid compatibility.
        #
        # PostgreSQL BIGSERIAL inserts ke baad
        # same DB session ka latest sequence ID.

        cursor = (
            self.connection
            .cursor()
        )

        try:

            cursor.execute(
                "SELECT LASTVAL()"
            )

            result = cursor.fetchone()

            if result:

                return result[0]

            return None

        finally:

            cursor.close()

# ============================================================
# ===== POSTGRES CURSOR WRAPPER END =====
# ============================================================


# ============================================================
# ===== POSTGRES CONNECTION WRAPPER START =====
# ============================================================

class PostgreSQLConnectionWrapper:

    def __init__(
        self,
        connection
    ):

        self.connection = (
            connection
        )


    @staticmethod
    def _convert_placeholders(
        query
    ):

        # Existing SQLite queries:
        #
        # WHERE id = ?
        #
        # PostgreSQL:
        #
        # WHERE id = %s

        return query.replace(
            "?",
            "%s"
        )


    @staticmethod
    def _prepare_datetime_parameter(
        value
    ):

        # Existing app datetime.now().isoformat()
        # strings use karta hai.
        #
        # Supabase TIMESTAMPTZ ke liye
        # local datetime ko timezone-aware banaya jayega.

        if (
            isinstance(
                value,
                str
            )
            and
            "T" in value
        ):

            try:

                parsed_value = (
                    datetime.fromisoformat(
                        value
                    )
                )

                if (
                    parsed_value.tzinfo
                    is None
                ):

                    parsed_value = (
                        parsed_value
                        .astimezone()
                    )

                return parsed_value

            except ValueError:

                pass

        return value


    @staticmethod
    def _prepare_parameters(
        query,
        parameters
    ):

        if parameters is None:

            return tuple()


        prepared = [

            PostgreSQLConnectionWrapper
            ._prepare_datetime_parameter(
                value
            )

            for value
            in parameters

        ]


        # Existing Fyloq SQLite me
        # one_time_download 0/1 hai.
        #
        # Supabase PostgreSQL schema me BOOLEAN hai.
        #
        # INSERT columns se exact position detect karke
        # bool me convert karte hain.

        normalized_query = (
            query
            .strip()
            .lower()
        )

        if normalized_query.startswith(
            "insert into files"
        ):

            match = re.search(
                r"insert\s+into\s+files\s*"
                r"\((.*?)\)\s*values",
                query,
                flags=(
                    re.IGNORECASE
                    |
                    re.DOTALL
                )
            )

            if match:

                columns = [

                    column.strip()

                    for column
                    in match.group(1).split(
                        ","
                    )

                ]

                if (
                    "one_time_download"
                    in columns
                ):

                    index = columns.index(
                        "one_time_download"
                    )

                    if index < len(
                        prepared
                    ):

                        prepared[
                            index
                        ] = bool(
                            prepared[
                                index
                            ]
                        )


        return tuple(
            prepared
        )


    def execute(
        self,
        query,
        parameters=None
    ):

        postgres_query = (
            self._convert_placeholders(
                query
            )
        )

        postgres_parameters = (
            self._prepare_parameters(
                query,
                parameters
            )
        )

        cursor = (
            self.connection
            .cursor()
        )

        if postgres_parameters:

            cursor.execute(
                postgres_query,
                postgres_parameters
            )

        else:

            cursor.execute(
                postgres_query
            )

        return PostgreSQLCursorWrapper(
            cursor,
            self.connection
        )


    def commit(
        self
    ):

        self.connection.commit()


    def rollback(
        self
    ):

        self.connection.rollback()


    def close(
        self
    ):

        self.connection.close()

# ============================================================
# ===== POSTGRES CONNECTION WRAPPER END =====
# ============================================================


# ============================================================
# ===== DATABASE CONNECTION START =====
# ============================================================

def get_database_connection():

    # ========================================================
    # SQLITE BACKUP MODE
    # ========================================================

    if IS_SQLITE:

        connection = sqlite3.connect(
            LOCAL_DATABASE_PATH
        )

        connection.row_factory = (
            sqlite3.Row
        )

        return connection


    # ========================================================
    # SUPABASE POSTGRESQL MODE
    # ========================================================

    connection = psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )

    return PostgreSQLConnectionWrapper(
        connection
    )

# ============================================================
# ===== DATABASE CONNECTION END =====
# ============================================================


# ============================================================
# ===== DATABASE TYPE HELPER START =====
# ============================================================

def is_sqlite_database():

    return IS_SQLITE


def get_database_provider():

    if IS_SQLITE:

        return "SQLite"

    if (
        "supabase"
        in DATABASE_URL.lower()
    ):

        return (
            "Supabase PostgreSQL"
        )

    return "PostgreSQL"

# ============================================================
# ===== DATABASE TYPE HELPER END =====
# ============================================================


# ============================================================
# ===== DATABASE CONNECTION TEST START =====
# ============================================================

def test_database_connection():

    connection = None

    try:

        connection = (
            get_database_connection()
        )

        result = connection.execute(
            "SELECT 1"
        ).fetchone()

        return (
            result is not None
            and
            result[0] == 1
        )

    except Exception as error:

        print(
            "Database connection failed:",
            error
        )

        return False

    finally:

        if connection:

            connection.close()

# ============================================================
# ===== DATABASE CONNECTION TEST END =====
# ============================================================