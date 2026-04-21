from unittest.mock import MagicMock, patch

from apps.evidence.hashing import hash_bytes
from apps.evidence.storage import store_evidence


class TestStoreEvidence:
    @patch("apps.evidence.storage.S3StorageClient")
    def test_returns_hash_and_url(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.upload.return_value = "https://bucket.s3.eu-west-1.amazonaws.com/evidence/ab/abc.txt"
        mock_client_cls.return_value = mock_client

        file_data = b"test file content"
        file_hash, url = store_evidence(file_data, "photo.jpg")

        assert file_hash == hash_bytes(file_data)
        assert url.startswith("https://")
        mock_client.upload.assert_called_once()

    @patch("apps.evidence.storage.S3StorageClient")
    def test_upload_key_contains_hash_prefix(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.upload.return_value = "https://example.com/file"
        mock_client_cls.return_value = mock_client

        store_evidence(b"data", "doc.pdf")
        call_args = mock_client.upload.call_args
        key = call_args[0][0]
        assert key.startswith("evidence/")
        assert key.endswith(".pdf")

    @patch("apps.evidence.storage.S3StorageClient")
    def test_file_without_extension_uses_bin(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.upload.return_value = "https://example.com/file"
        mock_client_cls.return_value = mock_client

        store_evidence(b"data", "noext")
        call_args = mock_client.upload.call_args
        key = call_args[0][0]
        assert key.endswith(".bin")
