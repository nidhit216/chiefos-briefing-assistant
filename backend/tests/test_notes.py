import pytest

from app.routers import notes as notes_router
from app.database import async_session
from app.models.note import Note


@pytest.fixture(autouse=True)
def stub_generate_tags(monkeypatch):
    """Default stub: no AI tags suggested, unless a test overrides it."""
    async def _fake(title, content):
        return []
    monkeypatch.setattr(notes_router, "generate_tags", _fake)
    return _fake


def use_ai_tags(monkeypatch, tags):
    async def _fake(title, content):
        return tags
    monkeypatch.setattr(notes_router, "generate_tags", _fake)


async def test_create_note_merges_user_tags_with_ai_tags(client, monkeypatch):
    use_ai_tags(monkeypatch, ["ai-suggested", "roadmap"])

    res = await client.post(
        "/notes/",
        json={"title": "Plan", "content": "content", "tags": ["manual"]},
    )

    assert res.status_code == 201
    data = res.json()
    assert data["tags"] == ["manual", "ai-suggested", "roadmap"]


async def test_create_note_without_user_tags_uses_only_ai_tags(client, monkeypatch):
    use_ai_tags(monkeypatch, ["solo-ai-tag"])

    res = await client.post("/notes/", json={"title": "Plan", "content": "content"})

    assert res.status_code == 201
    assert res.json()["tags"] == ["solo-ai-tag"]


async def test_create_note_when_ai_tagging_fails_still_succeeds(client):
    # autouse stub_generate_tags fixture simulates the "AI call failed" -> [] case
    res = await client.post(
        "/notes/",
        json={"title": "Plan", "content": "content", "tags": ["manual"]},
    )

    assert res.status_code == 201
    assert res.json()["tags"] == ["manual"]


async def test_create_note_with_no_tags_at_all_returns_null_tags(client):
    res = await client.post("/notes/", json={"title": "Plan", "content": "content"})

    assert res.status_code == 201
    assert res.json()["tags"] is None


async def test_create_note_dedupes_ai_tag_already_supplied_by_user(client, monkeypatch):
    use_ai_tags(monkeypatch, ["manual", "new-one"])

    res = await client.post(
        "/notes/",
        json={"title": "Plan", "content": "content", "tags": ["manual"]},
    )

    assert res.status_code == 201
    assert res.json()["tags"] == ["manual", "new-one"]


async def test_create_note_with_due_date_persists_it(client):
    res = await client.post(
        "/notes/",
        json={"title": "Plan", "content": "content", "due_date": "2026-07-01"},
    )

    assert res.status_code == 201
    assert res.json()["due_date"] == "2026-07-01"


async def test_create_note_without_due_date_is_null(client):
    res = await client.post("/notes/", json={"title": "Plan", "content": "content"})

    assert res.status_code == 201
    assert res.json()["due_date"] is None


async def test_create_note_missing_title_returns_422(client):
    res = await client.post("/notes/", json={"content": "content"})
    assert res.status_code == 422


async def test_create_note_with_malformed_due_date_returns_422(client):
    res = await client.post(
        "/notes/",
        json={"title": "Plan", "content": "content", "due_date": "not-a-date"},
    )
    assert res.status_code == 422


async def test_update_note_title_only_leaves_content_and_tags_untouched(client):
    created = await client.post(
        "/notes/",
        json={"title": "Original", "content": "original content", "tags": ["keep-me"]},
    )
    note_id = created.json()["id"]

    res = await client.put(f"/notes/{note_id}", json={"title": "Updated"})

    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Updated"
    assert data["content"] == "original content"
    assert data["tags"] == ["keep-me"]


async def test_update_note_without_due_date_in_payload_clears_existing_due_date(client):
    """due_date is assigned unconditionally on update (unlike title/content/tags) so the
    frontend's edit form — which always submits the current due-date state — can clear it
    by sending null. A consequence: any PUT that omits due_date wipes it."""
    created = await client.post(
        "/notes/",
        json={"title": "Original", "content": "content", "due_date": "2026-07-01"},
    )
    note_id = created.json()["id"]
    assert created.json()["due_date"] == "2026-07-01"

    res = await client.put(f"/notes/{note_id}", json={"title": "Updated"})

    assert res.status_code == 200
    assert res.json()["due_date"] is None


async def test_update_note_can_set_a_due_date(client):
    created = await client.post("/notes/", json={"title": "Plan", "content": "content"})
    note_id = created.json()["id"]

    res = await client.put(f"/notes/{note_id}", json={"due_date": "2026-08-15"})

    assert res.status_code == 200
    assert res.json()["due_date"] == "2026-08-15"


async def test_update_note_can_explicitly_clear_due_date(client):
    created = await client.post(
        "/notes/",
        json={"title": "Plan", "content": "content", "due_date": "2026-08-15"},
    )
    note_id = created.json()["id"]

    res = await client.put(f"/notes/{note_id}", json={"due_date": None})

    assert res.status_code == 200
    assert res.json()["due_date"] is None


async def test_update_note_tags_are_replaced_not_merged_with_ai_suggestions(client, monkeypatch):
    use_ai_tags(monkeypatch, ["should-not-appear"])
    created = await client.post(
        "/notes/",
        json={"title": "Plan", "content": "content", "tags": ["original"]},
    )
    note_id = created.json()["id"]

    res = await client.put(f"/notes/{note_id}", json={"tags": ["replaced"]})

    assert res.status_code == 200
    assert res.json()["tags"] == ["replaced"]


async def test_update_nonexistent_note_returns_404(client):
    res = await client.put(
        "/notes/00000000-0000-0000-0000-000000000000", json={"title": "X"}
    )
    assert res.status_code == 404


async def test_delete_note_then_get_returns_404(client):
    created = await client.post("/notes/", json={"title": "Plan", "content": "content"})
    note_id = created.json()["id"]

    delete_res = await client.delete(f"/notes/{note_id}")
    assert delete_res.status_code == 204

    get_res = await client.get(f"/notes/{note_id}")
    assert get_res.status_code == 404


async def test_other_users_note_is_invisible_for_get_update_delete(client, make_user):
    other = await make_user()
    async with async_session() as session:
        note = Note(user_id=other.id, title="Not yours", content="secret")
        session.add(note)
        await session.commit()
        await session.refresh(note)
        other_note_id = str(note.id)

    assert (await client.get(f"/notes/{other_note_id}")).status_code == 404
    assert (
        await client.put(f"/notes/{other_note_id}", json={"title": "hijacked"})
    ).status_code == 404
    assert (await client.delete(f"/notes/{other_note_id}")).status_code == 404


async def test_list_notes_filters_by_single_tag(client):
    await client.post("/notes/", json={"title": "A", "content": "c", "tags": ["work"]})
    await client.post("/notes/", json={"title": "B", "content": "c", "tags": ["personal"]})

    res = await client.get("/notes/", params={"tags": ["work"]})

    assert res.status_code == 200
    titles = [n["title"] for n in res.json()]
    assert titles == ["A"]


async def test_list_notes_filters_by_multiple_tags_uses_overlap_semantics(client):
    await client.post("/notes/", json={"title": "A", "content": "c", "tags": ["work"]})
    await client.post("/notes/", json={"title": "B", "content": "c", "tags": ["personal"]})
    await client.post("/notes/", json={"title": "C", "content": "c", "tags": ["other"]})

    res = await client.get("/notes/", params={"tags": ["work", "personal"]})

    assert res.status_code == 200
    titles = {n["title"] for n in res.json()}
    assert titles == {"A", "B"}


async def test_list_notes_filters_by_due_before(client):
    await client.post(
        "/notes/", json={"title": "Due soon", "content": "c", "due_date": "2026-07-01"}
    )
    await client.post(
        "/notes/", json={"title": "Due later", "content": "c", "due_date": "2026-09-01"}
    )

    res = await client.get("/notes/", params={"due_before": "2026-08-01"})

    assert res.status_code == 200
    titles = [n["title"] for n in res.json()]
    assert titles == ["Due soon"]


async def test_list_notes_due_before_excludes_notes_with_no_due_date(client):
    await client.post("/notes/", json={"title": "No due date", "content": "c"})
    await client.post(
        "/notes/", json={"title": "Has due date", "content": "c", "due_date": "2026-07-01"}
    )

    res = await client.get("/notes/", params={"due_before": "2026-12-01"})

    titles = [n["title"] for n in res.json()]
    assert titles == ["Has due date"]


async def test_list_notes_combined_tag_and_due_date_filters(client):
    await client.post(
        "/notes/",
        json={"title": "Match", "content": "c", "tags": ["work"], "due_date": "2026-07-01"},
    )
    await client.post(
        "/notes/",
        json={"title": "Wrong tag", "content": "c", "tags": ["personal"], "due_date": "2026-07-01"},
    )
    await client.post(
        "/notes/",
        json={"title": "Too late", "content": "c", "tags": ["work"], "due_date": "2026-12-01"},
    )

    res = await client.get(
        "/notes/", params={"tags": ["work"], "due_before": "2026-08-01"}
    )

    titles = [n["title"] for n in res.json()]
    assert titles == ["Match"]


async def test_list_notes_with_no_filters_returns_everything(client):
    await client.post("/notes/", json={"title": "A", "content": "c"})
    await client.post("/notes/", json={"title": "B", "content": "c"})

    res = await client.get("/notes/")

    titles = {n["title"] for n in res.json()}
    assert titles == {"A", "B"}


async def test_create_note_defaults_to_not_completed(client):
    res = await client.post("/notes/", json={"title": "Plan", "content": "content"})

    assert res.status_code == 201
    assert res.json()["completed"] is False


async def test_update_note_can_mark_completed(client):
    created = await client.post("/notes/", json={"title": "Plan", "content": "content"})
    note_id = created.json()["id"]

    res = await client.put(
        f"/notes/{note_id}",
        json={"title": "Plan", "content": "content", "completed": True},
    )

    assert res.status_code == 200
    assert res.json()["completed"] is True


async def test_update_note_can_unmark_completed(client):
    created = await client.post("/notes/", json={"title": "Plan", "content": "content"})
    note_id = created.json()["id"]
    await client.put(
        f"/notes/{note_id}",
        json={"title": "Plan", "content": "content", "completed": True},
    )

    res = await client.put(
        f"/notes/{note_id}",
        json={"title": "Plan", "content": "content", "completed": False},
    )

    assert res.status_code == 200
    assert res.json()["completed"] is False


async def test_update_note_without_completed_in_payload_leaves_it_untouched(client):
    created = await client.post("/notes/", json={"title": "Plan", "content": "content"})
    note_id = created.json()["id"]
    await client.put(
        f"/notes/{note_id}",
        json={"title": "Plan", "content": "content", "completed": True},
    )

    res = await client.put(f"/notes/{note_id}", json={"title": "Renamed"})

    assert res.status_code == 200
    assert res.json()["title"] == "Renamed"
    assert res.json()["completed"] is True
