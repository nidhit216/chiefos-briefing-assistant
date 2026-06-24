from sqlalchemy import select

from app.database import async_session
from app.models.brief_task import BriefTask
from app.services.brief_tasks import sync_brief_tasks


async def list_tasks_for(user_id):
    async with async_session() as session:
        result = await session.execute(select(BriefTask).where(BriefTask.user_id == user_id))
        return result.scalars().all()


async def test_sync_brief_tasks_inserts_new_items(test_user):
    brief_json = {
        "time_critical": [{"task": "File the report", "date": "Jun 25"}],
        "coming_soon": [{"task": "Plan offsite", "date": "Jul 1"}],
    }

    async with async_session() as session:
        await sync_brief_tasks(test_user, brief_json, session)
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    by_category = {t.category: t.task for t in tasks}
    assert by_category["time_critical"] == "File the report"
    assert by_category["coming_soon"] == "Plan offsite"
    assert all(t.completed is False for t in tasks)


async def test_sync_brief_tasks_matches_existing_task_case_insensitively_and_updates_date(
    test_user,
):
    async with async_session() as session:
        await sync_brief_tasks(
            test_user, {"time_critical": [{"task": "File the report", "date": "Jun 25"}]}, session
        )
        await session.commit()

    async with async_session() as session:
        await sync_brief_tasks(
            test_user, {"time_critical": [{"task": "FILE THE REPORT", "date": "Jun 26"}]}, session
        )
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    assert len(tasks) == 1
    assert tasks[0].date_label == "Jun 26"


async def test_sync_brief_tasks_leaves_completed_flag_untouched_on_regeneration(test_user):
    async with async_session() as session:
        await sync_brief_tasks(
            test_user, {"time_critical": [{"task": "File the report", "date": "Jun 25"}]}, session
        )
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    async with async_session() as session:
        task = await session.get(BriefTask, tasks[0].id)
        task.completed = True
        await session.commit()

    async with async_session() as session:
        await sync_brief_tasks(
            test_user, {"time_critical": [{"task": "File the report", "date": "Jun 30"}]}, session
        )
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    assert len(tasks) == 1
    assert tasks[0].completed is True
    assert tasks[0].date_label == "Jun 30"


async def test_sync_brief_tasks_never_deletes_tasks_not_seen_again(test_user):
    async with async_session() as session:
        await sync_brief_tasks(
            test_user, {"time_critical": [{"task": "Old task", "date": "Jun 25"}]}, session
        )
        await session.commit()

    async with async_session() as session:
        await sync_brief_tasks(
            test_user, {"time_critical": [{"task": "New task", "date": "Jun 30"}]}, session
        )
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    titles = {t.task for t in tasks}
    assert titles == {"Old task", "New task"}


async def test_sync_brief_tasks_handles_plain_string_items_for_priorities_and_focus_areas(test_user):
    brief_json = {
        "priorities": ["Ship the release"],
        "focus_areas": ["Deep work on Q3 planning"],
    }

    async with async_session() as session:
        await sync_brief_tasks(test_user, brief_json, session)
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    by_category = {t.category: t.task for t in tasks}
    assert by_category["priorities"] == "Ship the release"
    assert by_category["focus_areas"] == "Deep work on Q3 planning"
    assert all(t.date_label is None for t in tasks)


async def test_sync_brief_tasks_skips_items_with_blank_task_text(test_user):
    async with async_session() as session:
        await sync_brief_tasks(test_user, {"time_critical": [{"task": "  ", "date": "Jun 25"}]}, session)
        await session.commit()

    tasks = await list_tasks_for(test_user.id)
    assert tasks == []


async def test_list_brief_tasks_orders_incomplete_first(client, test_user):
    async with async_session() as session:
        await sync_brief_tasks(
            test_user,
            {
                "time_critical": [{"task": "Task A", "date": "Jun 25"}],
                "coming_soon": [{"task": "Task B", "date": "Jul 1"}],
            },
            session,
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
        await sync_brief_tasks(
            test_user,
            {
                "time_critical": [{"task": "Urgent task", "date": "Jun 25"}],
                "coming_soon": [{"task": "Later task", "date": "Jul 1"}],
            },
            session,
        )
        await session.commit()

    res = await client.get("/briefs/tasks", params={"category": "coming_soon"})

    assert res.status_code == 200
    tasks = res.json()
    assert [t["task"] for t in tasks] == ["Later task"]


async def test_list_brief_tasks_does_not_leak_other_users_tasks(client, test_user, make_user):
    other = await make_user()
    async with async_session() as session:
        await sync_brief_tasks(other, {"time_critical": [{"task": "Not yours", "date": "Jun 25"}]}, session)
        await sync_brief_tasks(test_user, {"time_critical": [{"task": "Yours", "date": "Jun 25"}]}, session)
        await session.commit()

    res = await client.get("/briefs/tasks")

    assert res.status_code == 200
    assert [t["task"] for t in res.json()] == ["Yours"]


async def test_patch_brief_task_toggles_completed(client, test_user):
    async with async_session() as session:
        await sync_brief_tasks(test_user, {"time_critical": [{"task": "Task A", "date": "Jun 25"}]}, session)
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
        await sync_brief_tasks(other, {"time_critical": [{"task": "Not yours", "date": "Jun 25"}]}, session)
        await session.commit()
    task = (await list_tasks_for(other.id))[0]

    res = await client.patch(f"/briefs/tasks/{task.id}", json={"completed": True})

    assert res.status_code == 404
