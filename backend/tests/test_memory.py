from app.database import async_session
from app.models.memory import Memory


async def seed_memory(user_id, content):
    async with async_session() as session:
        memory = Memory(user_id=user_id, content=content)
        session.add(memory)
        await session.commit()
        await session.refresh(memory)
        return memory


async def test_list_memories_returns_empty_when_none_exist(client):
    res = await client.get("/memories/")
    assert res.status_code == 200
    assert res.json() == []


async def test_list_memories_returns_newest_first(client, test_user):
    first = await seed_memory(test_user.id, "Older fact")
    second = await seed_memory(test_user.id, "Newer fact")

    res = await client.get("/memories/")

    assert res.status_code == 200
    contents = [m["content"] for m in res.json()]
    assert contents[0] == "Newer fact"
    assert contents[1] == "Older fact"
    assert {m["id"] for m in res.json()} == {str(first.id), str(second.id)}


async def test_list_memories_does_not_leak_other_users_memories(client, test_user, make_user):
    other = await make_user()
    await seed_memory(other.id, "Not yours")
    await seed_memory(test_user.id, "Yours")

    res = await client.get("/memories/")

    assert res.status_code == 200
    contents = [m["content"] for m in res.json()]
    assert contents == ["Yours"]


async def test_delete_memory_removes_it(client, test_user):
    memory = await seed_memory(test_user.id, "Forget me")

    res = await client.delete(f"/memories/{memory.id}")
    assert res.status_code == 204

    list_res = await client.get("/memories/")
    assert list_res.json() == []


async def test_delete_nonexistent_memory_returns_404(client):
    res = await client.delete("/memories/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


async def test_delete_other_users_memory_returns_404_and_leaves_it_intact(
    client, test_user, make_user
):
    other = await make_user()
    other_memory = await seed_memory(other.id, "Not yours")

    res = await client.delete(f"/memories/{other_memory.id}")
    assert res.status_code == 404

    async with async_session() as session:
        from sqlalchemy import select

        result = await session.execute(select(Memory).where(Memory.id == other_memory.id))
        assert result.scalar_one_or_none() is not None
