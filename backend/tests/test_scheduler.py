from app.services import scheduler as scheduler_service


async def test_sync_all_users_syncs_emails_and_calendar_for_every_user(test_user, make_user, monkeypatch):
    other = await make_user("Other User")
    calls = []

    async def fake_sync_emails(user, db):
        calls.append(("emails", user.id))

    async def fake_sync_calendar(user, db):
        calls.append(("calendar", user.id))

    monkeypatch.setattr(scheduler_service, "sync_emails", fake_sync_emails)
    monkeypatch.setattr(scheduler_service, "sync_calendar", fake_sync_calendar)

    await scheduler_service.sync_all_users()

    expected_users = {test_user.id, other.id}
    assert expected_users <= {uid for kind, uid in calls if kind == "emails"}
    assert expected_users <= {uid for kind, uid in calls if kind == "calendar"}


async def test_sync_all_users_keeps_going_after_one_user_fails(test_user, make_user, monkeypatch):
    other = await make_user("Other User")
    synced = []

    async def flaky_sync_emails(user, db):
        if user.id == test_user.id:
            raise RuntimeError("simulated sync failure")
        synced.append(user.id)

    async def noop_sync_calendar(user, db):
        synced.append(user.id)

    monkeypatch.setattr(scheduler_service, "sync_emails", flaky_sync_emails)
    monkeypatch.setattr(scheduler_service, "sync_calendar", noop_sync_calendar)

    await scheduler_service.sync_all_users()

    assert other.id in synced


def test_start_scheduler_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(scheduler_service.settings, "scheduled_sync_enabled", False)
    scheduler_service.start_scheduler()
    assert scheduler_service.scheduler.running is False
