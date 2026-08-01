# ============================================================
# FYLOQ APPLICATION-LEVEL FILE ENCRYPTION
# File: file_encryption.py
# ============================================================

import base64
import os
import secrets
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


ENCRYPTION_ALGORITHM = "AES-256-GCM"
ENCRYPTION_VERSION = 1

DATA_KEY_SIZE_BYTES = 32
NONCE_SIZE_BYTES = 12

MASTER_KEY_ENV_NAME = "FILE_ENCRYPTION_MASTER_KEY"

FILE_AAD_PREFIX = b"fyloq-file:v1:"
KEY_WRAP_AAD = b"fyloq-key-wrap:v1"


@dataclass(frozen=True)
class EncryptedFileResult:
    encrypted_data: bytes
    file_nonce: str
    wrapped_data_key: str
    key_wrap_nonce: str
    encryption_algorithm: str
    encryption_version: int
    encryption_key_version: int
    encrypted_size: int


def encode_base64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def decode_base64(encoded_data: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(encoded_data.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as error:
        raise ValueError("Invalid encryption metadata.") from error


def get_master_encryption_key() -> bytes:
    encoded_master_key = os.getenv(
        MASTER_KEY_ENV_NAME,
        ""
    ).strip()

    if not encoded_master_key:
        raise RuntimeError(
            f"{MASTER_KEY_ENV_NAME} is not configured."
        )

    try:
        master_key = base64.urlsafe_b64decode(
            encoded_master_key.encode("ascii")
        )
    except (ValueError, UnicodeEncodeError) as error:
        raise RuntimeError(
            f"{MASTER_KEY_ENV_NAME} must be a valid URL-safe Base64 value."
        ) from error

    if len(master_key) != DATA_KEY_SIZE_BYTES:
        raise RuntimeError(
            f"{MASTER_KEY_ENV_NAME} must decode to exactly 32 bytes."
        )

    return master_key


def build_file_aad(stored_filename: str) -> bytes:
    if not stored_filename:
        raise ValueError(
            "Stored filename is required for encryption."
        )

    return FILE_AAD_PREFIX + stored_filename.encode("utf-8")


def encrypt_file_data(
    file_data: bytes,
    stored_filename: str,
    encryption_key_version: int = 1
) -> EncryptedFileResult:

    if not isinstance(file_data, bytes):
        raise TypeError(
            "File data must be provided as bytes."
        )

    if not file_data:
        raise ValueError(
            "Empty files cannot be encrypted."
        )

    if encryption_key_version < 1:
        raise ValueError(
            "Encryption key version must be at least 1."
        )

    master_key = get_master_encryption_key()

    data_key = secrets.token_bytes(DATA_KEY_SIZE_BYTES)
    file_nonce = secrets.token_bytes(NONCE_SIZE_BYTES)
    key_wrap_nonce = secrets.token_bytes(NONCE_SIZE_BYTES)

    file_aad = build_file_aad(stored_filename)

    encrypted_data = AESGCM(data_key).encrypt(
        file_nonce,
        file_data,
        file_aad
    )

    wrapped_data_key = AESGCM(master_key).encrypt(
        key_wrap_nonce,
        data_key,
        KEY_WRAP_AAD
    )

    return EncryptedFileResult(
        encrypted_data=encrypted_data,
        file_nonce=encode_base64(file_nonce),
        wrapped_data_key=encode_base64(wrapped_data_key),
        key_wrap_nonce=encode_base64(key_wrap_nonce),
        encryption_algorithm=ENCRYPTION_ALGORITHM,
        encryption_version=ENCRYPTION_VERSION,
        encryption_key_version=encryption_key_version,
        encrypted_size=len(encrypted_data)
    )


def decrypt_file_data(
    encrypted_data: bytes,
    stored_filename: str,
    file_nonce: str,
    wrapped_data_key: str,
    key_wrap_nonce: str
) -> bytes:

    if not isinstance(encrypted_data, bytes):
        raise TypeError(
            "Encrypted file data must be bytes."
        )

    if not encrypted_data:
        raise ValueError(
            "Encrypted file data is empty."
        )

    master_key = get_master_encryption_key()

    decoded_file_nonce = decode_base64(file_nonce)
    decoded_wrapped_data_key = decode_base64(wrapped_data_key)
    decoded_key_wrap_nonce = decode_base64(key_wrap_nonce)

    if len(decoded_file_nonce) != NONCE_SIZE_BYTES:
        raise ValueError(
            "Invalid file encryption nonce."
        )

    if len(decoded_key_wrap_nonce) != NONCE_SIZE_BYTES:
        raise ValueError(
            "Invalid key-wrap nonce."
        )

    try:
        data_key = AESGCM(master_key).decrypt(
            decoded_key_wrap_nonce,
            decoded_wrapped_data_key,
            KEY_WRAP_AAD
        )

        if len(data_key) != DATA_KEY_SIZE_BYTES:
            raise ValueError(
                "Invalid decrypted data key."
            )

        file_aad = build_file_aad(stored_filename)

        return AESGCM(data_key).decrypt(
            decoded_file_nonce,
            encrypted_data,
            file_aad
        )

    except InvalidTag as error:
        raise ValueError(
            "File decryption failed. The encrypted file, "
            "metadata, or master key is invalid."
        ) from error