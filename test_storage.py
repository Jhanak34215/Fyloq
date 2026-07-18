# ============================================================
# FYLOQ SUPABASE STORAGE TEST
# File: test_storage.py
# ============================================================

import uuid

from storage import (
    upload_file_to_storage,
    download_file_from_storage,
    delete_file_from_storage
)


def test_storage():

    test_filename = (
        "storage-test/"
        +
        uuid.uuid4().hex
        +
        ".txt"
    )

    test_content = (
        b"Fyloq Supabase Storage Test"
    )

    print("\n1. Uploading test file...")

    upload_file_to_storage(
        test_filename,
        test_content,
        "text/plain"
    )

    print("✅ Upload successful")


    print("\n2. Downloading test file...")

    downloaded_content = (
        download_file_from_storage(
            test_filename
        )
    )

    if downloaded_content != test_content:

        raise RuntimeError(
            "Downloaded file content does not match uploaded content."
        )

    print("✅ Download successful")
    print("✅ File content verified")


    print("\n3. Deleting test file...")

    delete_file_from_storage(
        test_filename
    )

    print("✅ Delete successful")


    print(
        "\n✅ SUPABASE STORAGE TEST "
        "COMPLETED SUCCESSFULLY"
    )


if __name__ == "__main__":

    try:

        test_storage()

    except Exception as error:

        print(
            "\n❌ SUPABASE STORAGE TEST FAILED"
        )

        print(
            "Error:",
            error
        )