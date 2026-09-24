from sqlalchemy.orm import configure_mappers

from app.database import models  # noqa: F401
from app.database.base import Base


def test_all_model_relationships_resolve() -> None:
    configure_mappers()

    relationships = {
        f"{mapper.class_.__name__}.{relationship.key}"
        for mapper in Base.registry.mappers
        for relationship in mapper.relationships
    }

    assert relationships == {
        "User.chat_threads",
        "ChatThread.owner",
        "ChatThread.messages",
        "ChatMessage.thread",
        "ChatMessage.citations",
        "SourceDocument.chunks",
        "DocumentChunk.document",
        "DocumentChunk.citations",
        "MessageCitation.message",
        "MessageCitation.chunk",
    }


def test_all_foreign_keys_target_known_tables() -> None:
    configure_mappers()
    tables = Base.metadata.tables

    for table in tables.values():
        for foreign_key in table.foreign_keys:
            target_table = foreign_key.target_fullname.split(".", 1)[0]
            assert target_table in tables
