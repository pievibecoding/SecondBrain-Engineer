from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from backend.models.conversation import Conversation, Message


async def get_or_create_conversation(db: AsyncSession, user_id: str, conversation_id: str | None, first_message: str | None = None) -> Conversation:
    if conversation_id:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conv = result.scalar_one_or_none()
        if conv is None or str(conv.user_id) != str(user_id):
            raise NoResultFound("Conversation not found or not owned")
        return conv

    # create
    conv = Conversation(user_id=user_id)
    if first_message:
        conv.title = (first_message.strip()[:80])
    db.add(conv)
    await db.flush()
    return conv


async def add_message(db: AsyncSession, conversation_id: str, role: str, content: str, citations: list | None = None, graphiti_synced: bool = False) -> Message:
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if conv is None:
        raise NoResultFound("Conversation not found")

    msg = Message(conversation_id=conversation_id, role=role, content=content, citations=citations)
    msg.graphiti_synced = graphiti_synced
    db.add(msg)
    conv.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return msg


async def list_conversations(db: AsyncSession, user_id: str, limit: int = 50, offset: int = 0) -> list[Conversation]:
    result = await db.execute(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).limit(limit).offset(offset))
    return result.scalars().all()


async def list_messages(db: AsyncSession, user_id: str, conversation_id: str) -> list[Message]:
    # ensure ownership
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if conv is None or str(conv.user_id) != str(user_id):
        raise NoResultFound("Conversation not found or not owned")

    result = await db.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()))
    return result.scalars().all()
