import hashlib
import os

DATAPACK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "source", "Assignment_2_DataPack.pdf"
)
EXPECTED_SIZE = 38129
EXPECTED_SHA256 = "21a5ed364ef5063f10b73e349da3665270c1db3fe51f85be91f8e3e347805c50"


def test_datapack_exists():
    """Verify that the authoritative DataPack PDF exists at the expected path."""
    assert os.path.exists(DATAPACK_PATH), f"DataPack not found at {DATAPACK_PATH}"
    assert os.path.isfile(DATAPACK_PATH), f"DataPack at {DATAPACK_PATH} is not a file"


def test_datapack_byte_size():
    """Verify that the DataPack PDF preserves the exact byte size of the authoritative source."""
    actual_size = os.path.getsize(DATAPACK_PATH)
    assert actual_size == EXPECTED_SIZE, (
        f"DataPack size mismatch: expected {EXPECTED_SIZE} bytes, got {actual_size} bytes"
    )


def test_datapack_sha256_integrity():
    """Verify that the DataPack PDF SHA-256 hash matches the authoritative source."""
    hasher = hashlib.sha256()
    with open(DATAPACK_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest().lower()
    assert actual_hash == EXPECTED_SHA256, (
        f"DataPack SHA256 mismatch: expected {EXPECTED_SHA256}, got {actual_hash}"
    )
