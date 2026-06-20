import pytest
import types
from uuid import uuid4
from sqlalchemy.exc import NoResultFound

from backend.services.conversation_service import get_or_create_conversation, add_message, list_conversations, list_messages
from backend.models.conversation import Conversation, Message


# ──────────────────────────────────────────
# Minimal async fake session
# ──────────────────────────────────────────

def _make_conv(user_id="user-1", conv_id=None):
    c = types.SimpleNamespace()
    c.id = conv_id or uuid4()
    c.user_id = user_id
    c.title = None
    c.updated_at = None
    return c


class FakeResult:
    def __init__(self, obj=None, rows=None):
        self._obj = obj
        self._rows = rows or []

    def scalar_one_or_none(self):
        return self._obj

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, stored_conv=None, stored_msgs=None):
        self._conv = stored_conv
        self._msgs = stored_msgs or []
        self.added = []

    async def execute(self, stmt):
        # simple dispatch by guessing from stored state
        if self._conv is not None:
            return FakeResult(self._conv)
        return FakeResult(None, self._msgs)

    async def flush(self):
        pass

    def add(self, obj):
        self.added.append(obj)


# ──────────────────────────────────────────
# Tests
# ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_or_create_creates_when_no_conv_id():
    db = FakeSession(stored_conv=None)
    conv = await get_or_create_conversation(db, "user-1", None, "first message")
    assert conv is not None
    # should have been added to session
    assert conv in db.added


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_when_owner_matches():
    existing = _make_conv(user_id="user-1")
    db = FakeSession(stored_conv=existing)
    result = await get_or_create_conversation(db, "user-1", str(existing.id))
    assert result.id == existing.id


@pytest.mark.asyncio
async def test_get_or_create_raises_when_wrong_owner():
    existing = _make_conv(user_id="user-other")
    db = FakeSession(stored_conv=existing)
    with pytest.raises(NoResultFound):
        await get_or_create_conversation(db, "user-1", str(existing.id))


@pytest.mark.asyncio
async def test_add_message_flushes():
    existing = _make_conv(user_id="user-1")
    db = FakeSession(stored_conv=existing)
    msg = await add_message(db, str(existing.id), "user", "hello")
    assert msg.role == "user"
    assert msg.content == "hello"
    assert msg in db.added
