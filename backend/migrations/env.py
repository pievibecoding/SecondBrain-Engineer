import asyncio
import os
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import models so metadata is available
from backend.models.base import Base
from backend.models.user import User
from backend.models.conversation import Conversation, Message
from backend.models.nas_file import NasFile
from backend.models.nas_folder import NasFolder

config = context.config
target_metadata = Base.metadata

# Read DATABASE_URL directly from environment — bypasses pydantic Settings
# so that docker exec with env override works correctly.
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Fallback to settings if env var not set directly
    from backend.config import settings
    DATABASE_URL = settings.DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
