from unittest.mock import AsyncMock

from app.routers import search as search_router


async def test_search_returns_results_from_semantic_search(client, monkeypatch):
    fake_results = [
        {"id": "1", "source_type": "note", "source_id": "n1", "content": "Plan the roadmap", "similarity": 0.91},
    ]
    monkeypatch.setattr(search_router, "semantic_search", AsyncMock(return_value=fake_results))

    res = await client.get("/search/", params={"q": "roadmap"})

    assert res.status_code == 200
    assert res.json() == fake_results


async def test_search_passes_source_type_and_limit_through(client, monkeypatch):
    mock_search = AsyncMock(return_value=[])
    monkeypatch.setattr(search_router, "semantic_search", mock_search)

    await client.get("/search/", params={"q": "roadmap", "source_type": "note", "limit": 5})

    _, kwargs = mock_search.call_args
    assert kwargs["query"] == "roadmap"
    assert kwargs["source_type"] == "note"
    assert kwargs["limit"] == 5


async def test_search_missing_query_returns_422(client):
    res = await client.get("/search/")
    assert res.status_code == 422


async def test_search_empty_query_returns_422(client):
    res = await client.get("/search/", params={"q": ""})
    assert res.status_code == 422


async def test_search_limit_above_max_returns_422(client):
    res = await client.get("/search/", params={"q": "x", "limit": 100})
    assert res.status_code == 422


async def test_search_limit_below_min_returns_422(client):
    res = await client.get("/search/", params={"q": "x", "limit": 0})
    assert res.status_code == 422


async def test_embed_user_data_returns_counts_and_message(client, monkeypatch):
    monkeypatch.setattr(
        search_router,
        "embed_all_user_data",
        AsyncMock(return_value={"emails": 2, "notes": 3, "events": 1}),
    )

    res = await client.post("/search/embed")

    assert res.status_code == 200
    data = res.json()
    assert data["emails"] == 2
    assert data["notes"] == 3
    assert data["events"] == 1
    assert "6" in data["message"]
