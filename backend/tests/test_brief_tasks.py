from sqlalchemy import select

from app.database import async_session
from app.models.brief_task import BriefTask
from app.services.brief_tasks import sync_brief_tasks


async def list_tasks_for(user_id):
    async with async_session() as session:
        result = await session.execute(select(BriefTask).where(BriefTask.user_id == user_id))
        return result.scalars().all()


async def test_sync_brief_tasks_inserts_new_items(test_user):
    brief_json = {"attention_required": ["File the report"]}

    async with async_session() as session:
        await sync_brief_tasks(test_user, brief_json, session)
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    by_category = {t.category: t.task for t in tasks}
    assert by_category["attention_required"] == "File the report"
    assert all(t.completed is False for t in tasks)


async def test_sync_brief_tasks_matches_existing_task_case_insensitively(test_user):
    async with async_session() as session:
        await sync_brief_tasks(test_user, {"attention_required": ["File the report"]}, session)
        await session.commit()

    async with async_session() as session:
        await sync_brief_tasks(test_user, {"attention_required": ["FILE THE REPORT"]}, session)
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    assert len(tasks) == 1


async def test_sync_brief_tasks_leaves_completed_flag_untouched_on_regeneration(test_user):
    async with async_session() as session:
        await sync_brief_tasks(test_user, {"attention_required": ["File the report"]}, session)
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    async with async_session() as session:
        task = await session.get(BriefTask, tasks[0].id)
        task.completed = True
        await session.commit()

    async with async_session() as session:
        await sync_brief_tasks(test_user, {"attention_required": ["File the report"]}, session)
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    assert len(tasks) == 1
    assert tasks[0].completed is True


async def test_sync_brief_tasks_never_deletes_tasks_not_seen_again(test_user):
    async with async_session() as session:
        await sync_brief_tasks(test_user, {"attention_required": ["Old task"]}, session)
        await session.commit()

    async with async_session() as session:
        await sync_brief_tasks(test_user, {"attention_required": ["New task"]}, session)
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    titles = {t.task for t in tasks}
    assert titles == {"Old task", "New task"}


async def test_sync_brief_tasks_skips_items_with_blank_task_text(test_user):
    async with async_session() as session:
        await sync_brief_tasks(test_user, {"attention_required": ["  "]}, session)
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    assert tasks == []


async def test_sync_brief_tasks_ignores_unknown_categories(test_user):
    async with async_session() as session:
        await sync_brief_tasks(test_user, {"priorities": ["Ship the release"]}, session)
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    assert tasks == []


async def test_list_brief_tasks_orders_incomplete_first(client, test_user):
    async with async_session() as session:
        await sync_brief_tasks(
            test_user, {"attention_required": ["Task A", "Task B"]}, session
        )
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    completed_task = next(t for t in tasks if t.task == "Task A")
    async with async_session() as session:
        task = await session.get(BriefTask, completed_task.id)
        task.completed = True
        await session.commit()

    res = await client.get("/briefs/tasks")

    assert res.status_code == 200
    data = res.json()
    assert data[-1]["task"] == "Task A"
    assert data[-1]["completed"] is True


async def test_list_brief_tasks_filters_by_category(client, test_user):
    async with async_session() as session:
        await sync_brief_tasks(test_user, {"attention_required": ["Urgent task"]}, session)
        await session.commit()

    res = await client.get("/briefs/tasks", params={"category": "nonexistent"})

    assert res.status_code == 200
    assert res.json() == []


async def test_list_brief_tasks_does_not_leak_other_users_tasks(client, test_user, make_user):
    other = await make_user()
    async with async_session() as session:
        await sync_brief_tasks(other, {"attention_required": ["Not yours"]}, session)
        await sync_brief_tasks(test_user, {"attention_required": ["Yours"]}, session)
        await session.commit()

    res = await client.get("/briefs/tasks")

    assert res.status_code == 200
    assert [t["task"] for t in res.json()] == ["Yours"]


async def test_patch_brief_task_toggles_completed(client, test_user):
    async with async_session() as session:
        await sync_brief_tasks(test_user, {"attention_required": ["Task A"]}, session)
        await session.commit()
    task = (await list_tasks_for(test_user.id))[0]

    res = await client.patch(f"/briefs/tasks/{task.id}", json={"completed": True})

    assert res.status_code == 200
    assert res.json()["completed"] is True


async def test_patch_nonexistent_brief_task_returns_404(client):
    res = await client.patch(
        "/briefs/tasks/00000000-0000-0000-0000-000000000000", json={"completed": True}
    )
    assert res.status_code == 404


async def test_patch_other_users_brief_task_returns_404(client, test_user, make_user):
    other = await make_user()
    async with async_session() as session:
        await sync_brief_tasks(other, {"attention_required": ["Not yours"]}, session)
        await session.commit()
    task = (await list_tasks_for(other.id))[0]

    res = await client.patch(f"/briefs/tasks/{task.id}", json={"completed": True})

    assert res.status_code == 404
