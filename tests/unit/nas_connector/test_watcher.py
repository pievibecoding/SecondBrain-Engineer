import asyncio
from nas_connector.watcher import compute_md5, poll_once
from nas_connector.uploader import Uploader


def test_compute_md5(tmp_path):
    p = tmp_path / "file.pdf"
    p.write_bytes(b"hello world")
    h = compute_md5(p)
    assert isinstance(h, str) and len(h) == 32


import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_pdf_triggers_report_new_with_content(tmp_path, monkeypatch):
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"fake pdf content")

    class MockUploader:
        async def get_hash(self, path):
            return None

        async def report_new(self, nas_path, file_hash, extension, ingest_content):
            assert ingest_content is True

    uploader = MockUploader()
    await poll_once(str(tmp_path), uploader)
