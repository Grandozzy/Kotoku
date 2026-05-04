from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _mock_s3_upload():
    with patch(
        "apps.vault.tasks.S3StorageClient.upload",
        return_value="https://s3.example.com/vault/mock.pdf",
    ):
        yield
