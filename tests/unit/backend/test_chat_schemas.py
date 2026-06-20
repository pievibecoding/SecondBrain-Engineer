import pytest
from pydantic import ValidationError
from backend.schemas.chat import ChatRequest, CitationItem, ChatResponse


def test_empty_message_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_whitespace_only_message_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(message="   ")


def test_valid_message_passes():
    req = ChatRequest(message="  Hello world  ")
    assert req.message == "Hello world"  # stripped


def test_conversation_id_optional():
    req = ChatRequest(message="hello")
    assert req.conversation_id is None


def test_citation_item_all_optional():
    c = CitationItem(type="document")
    assert c.file is None
    assert c.page is None


def test_chat_response_defaults():
    resp = ChatResponse(conversation_id="abc", answer="ok", citations=[])
    assert resp.query_mode == "mix"
    assert resp.latency_ms is None
