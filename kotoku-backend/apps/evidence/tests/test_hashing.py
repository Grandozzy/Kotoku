import hashlib

from apps.evidence.hashing import hash_bytes


class TestHashBytes:
    def test_returns_sha256_hex_digest(self):
        data = b"hello"
        expected = hashlib.sha256(data).hexdigest()
        assert hash_bytes(data) == expected

    def test_empty_bytes(self):
        expected = hashlib.sha256(b"").hexdigest()
        assert hash_bytes(b"") == expected

    def test_different_inputs_produce_different_hashes(self):
        assert hash_bytes(b"foo") != hash_bytes(b"bar")

    def test_deterministic(self):
        data = b"consistent input"
        assert hash_bytes(data) == hash_bytes(data)
