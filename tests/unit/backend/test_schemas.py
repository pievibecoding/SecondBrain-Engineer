import pytest
from pydantic import ValidationError
from backend.schemas.auth import RegisterRequest, LoginRequest, UserResponse
from backend.schemas.nas import DocumentResponse, FolderRequest, NasReportRequest


def test_password_too_short():
    with pytest.raises(ValidationError):
        RegisterRequest(username="user", email="a@b.com", password="short")


def test_invalid_email_format():
    with pytest.raises(ValidationError):
        RegisterRequest(username="user", email="not-an-email", password="valid_pass_123")


def test_login_validation():
    with pytest.raises(ValidationError):
        LoginRequest(email="", password="")


def test_nas_report_valid_events():
    for event in ["new", "changed", "deleted"]:
        schema = NasReportRequest(event=event, nas_path="/mnt/nas/test.pdf")
        assert schema.event == event


def test_nas_report_invalid_event():
    with pytest.raises(ValidationError):
        NasReportRequest(event="bad", nas_path="/mnt/nas/test.pdf")


def test_folder_request_valid_types():
    for folder_type in ["auto", "manual"]:
        schema = FolderRequest(path="/mnt/nas", folder_type=folder_type)
        assert schema.folder_type == folder_type


def test_folder_request_invalid_type():
    with pytest.raises(ValidationError):
        FolderRequest(path="/mnt/nas", folder_type="bad")


def test_document_response_validates_from_attributes():
    class Document:
        id = "file-1"
        nas_path = "/mnt/nas/a.pdf"
        folder_type = "auto"
        status = "indexed"
        file_hash = "hash-1"
        lightrag_doc_id = "doc-1"
        indexed_at = None
        created_at = "2026-01-01T00:00:00"
        error_msg = None
        chunk_count = None

    response = DocumentResponse.model_validate(Document())

    assert response.id == "file-1"
    assert response.chunk_count is None
