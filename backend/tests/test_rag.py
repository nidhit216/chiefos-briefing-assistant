"""Regression coverage for semantic_search's raw SQL: it previously used the
`:query_embedding::vector` syntax, which SQLAlchemy's text() mis-parses (the `::`
escapes to a literal colon), producing `syntax error at or near ":"` against Postgres.
Fixed by switching to CAST(:query_embedding AS vector). These tests exercise the
real query against the real pgvector-backed table, so a regression would fail loudly."""
import uuid
from unittest.mock import AsyncMock

from sqlalchemy import delete

from app.database import async_session
from app.models.embedding import DocumentEmbedding
from app.services import rag as rag_service

DIMENSIONS = 384


def make_vector(hot_index: int, magnitude: float = 1.0) -> list[float]:
    vec = [0.0] * DIMENSIONS
    vec[hot_index] = magnitude
    return vec


async def seed_embedding(user_id, source_type, content_text, embedding, source_id=None):
    async with async_session() as session:
        doc = DocumentEmbedding(
            id=uuid.uuid4(),
            user_id=user_id,
            source_type=source_type,
            source_id=source_id or uuid.uuid4(),
            content_text=content_text,
            embedding=embedding,
        )
        session.add(doc)
        await session.commit()


async def cleanup_embeddings(user_id):
    async with async_session() as session:
        await session.execute(delete(DocumentEmbedding).where(DocumentEmbedding.user_id == user_id))
        await session.commit()


async def test_semantic_search_executes_without_sql_syntax_error_and_ranks_by_similarity(
    test_user, monkeypatch
):
    await seed_embedding(test_user.id, "note", "closest match", make_vector(0))
    await seed_embedding(test_user.id, "note", "far match", make_vector(1))
    monkeypatch.setattr(rag_service, "generate_embedding", AsyncMock(return_value=make_vector(0)))

    try:
        async with async_session() as session:
            results = await rag_service.semantic_search("query", test_user.id, session)

        assert len(results) == 2
        assert results[0]["content"] == "closest match"
        assert results[0]["similarity"] > results[1]["similarity"]
    finally:
        await cleanup_embeddings(test_user.id)


async def test_semantic_search_filters_by_source_type(test_user, monkeypatch):
    await seed_embedding(test_user.id, "note", "a note", make_vector(0))
    await seed_embedding(test_user.id, "email", "an email", make_vector(0))
    monkeypatch.setattr(rag_service, "generate_embedding", AsyncMock(return_value=make_vector(0)))

    try:
        async with async_session() as session:
            results = await rag_service.semantic_search(
                "query", test_user.id, session, source_type="email"
            )

        assert len(results) == 1
        assert results[0]["content"] == "an email"
    finally:
        await cleanup_embeddings(test_user.id)


async def test_semantic_search_respects_limit(test_user, monkeypatch):
    for i in range(5):
        await seed_embedding(test_user.id, "note", f"note {i}", make_vector(i))
    monkeypatch.setattr(rag_service, "generate_embedding", AsyncMock(return_value=make_vector(0)))

    try:
        async with async_session() as session:
            results = await rag_service.semantic_search("query", test_user.id, session, limit=2)

        assert len(results) == 2
    finally:
        await cleanup_embeddings(test_user.id)


async def test_semantic_search_does_not_leak_other_users_embeddings(test_user, make_user, monkeypatch):
    other = await make_user()

    await seed_embedding(other.id, "note", "not yours", make_vector(0))
    await seed_embedding(test_user.id, "note", "yours", make_vector(0))
    monkeypatch.setattr(rag_service, "generate_embedding", AsyncMock(return_value=make_vector(0)))

    try:
        async with async_session() as session:
            results = await rag_service.semantic_search("query", test_user.id, session)

        assert [r["content"] for r in results] == ["yours"]
    finally:
        await cleanup_embeddings(test_user.id)
        await cleanup_embeddings(other.id)


async def test_semantic_search_returns_empty_list_when_nothing_matches(test_user, monkeypatch):
    monkeypatch.setattr(rag_service, "generate_embedding", AsyncMock(return_value=make_vector(0)))

    async with async_session() as session:
        results = await rag_service.semantic_search("query", test_user.id, session)

    assert results == []


async def test_get_relevant_context_formats_results(test_user, monkeypatch):
    await seed_embedding(test_user.id, "note", "important note content", make_vector(0))
    monkeypatch.setattr(rag_service, "generate_embedding", AsyncMock(return_value=make_vector(0)))

    try:
        async with async_session() as session:
            context = await rag_service.get_relevant_context("query", test_user.id, session)

        assert "important note content" in context
        assert "[note]" in context
    finally:
        await cleanup_embeddings(test_user.id)


async def test_get_relevant_context_returns_placeholder_when_no_matches(test_user, monkeypatch):
    monkeypatch.setattr(rag_service, "generate_embedding", AsyncMock(return_value=make_vector(0)))

    async with async_session() as session:
        context = await rag_service.get_relevant_context("query", test_user.id, session)

    assert context == "No relevant context found."
