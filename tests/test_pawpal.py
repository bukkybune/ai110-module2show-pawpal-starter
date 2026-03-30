from datetime import date, timedelta

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_owner(minutes=120):
    owner = Owner(name="Dorcas", available_minutes_per_day=minutes)
    return owner

def make_task(name="Task", duration=10, priority=Priority.MEDIUM,
              scheduled_time="", is_recurring=False, frequency="daily"):
    return Task(name=name, category="general", duration_minutes=duration,
                priority=priority, scheduled_time=scheduled_time,
                is_recurring=is_recurring, frequency=frequency)


# ── Existing tests ─────────────────────────────────────────────────────────────

def test_mark_complete_changes_status():
    task = make_task()
    assert task.is_complete is False
    task.mark_complete()
    assert task.is_complete is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Buddy", species="Dog", age=3)
    assert len(pet.get_tasks()) == 0
    pet.add_task(make_task())
    assert len(pet.get_tasks()) == 1


# ── Sorting ────────────────────────────────────────────────────────────────────

def test_sort_by_time_returns_chronological_order():
    owner = make_owner()
    scheduler = Scheduler(owner)
    tasks = [
        make_task("Evening", scheduled_time="18:00"),
        make_task("Morning", scheduled_time="07:00"),
        make_task("Midday",  scheduled_time="12:00"),
    ]
    result = scheduler.sort_by_time(tasks)
    assert [t.name for t in result] == ["Morning", "Midday", "Evening"]


def test_sort_by_time_places_unscheduled_tasks_last():
    owner = make_owner()
    scheduler = Scheduler(owner)
    tasks = [
        make_task("No Time"),
        make_task("Early",   scheduled_time="06:00"),
    ]
    result = scheduler.sort_by_time(tasks)
    assert result[0].name == "Early"
    assert result[-1].name == "No Time"


def test_sort_by_time_all_unscheduled_returns_all_tasks():
    owner = make_owner()
    scheduler = Scheduler(owner)
    tasks = [make_task("A"), make_task("B"), make_task("C")]
    result = scheduler.sort_by_time(tasks)
    assert len(result) == 3


# ── Recurrence ─────────────────────────────────────────────────────────────────

def test_complete_daily_task_creates_next_occurrence():
    owner = make_owner()
    pet = Pet(name="Buddy", species="Dog", age=3)
    task = make_task("Walk", is_recurring=True, frequency="daily")
    pet.add_task(task)
    owner.add_pet(pet)

    scheduler = Scheduler(owner)
    next_task = scheduler.complete_task(task)

    assert next_task is not None
    assert next_task.due_date == (date.today() + timedelta(days=1)).isoformat()


def test_complete_weekly_task_creates_next_occurrence_seven_days_out():
    owner = make_owner()
    pet = Pet(name="Buddy", species="Dog", age=3)
    task = make_task("Bath", is_recurring=True, frequency="weekly")
    pet.add_task(task)
    owner.add_pet(pet)

    scheduler = Scheduler(owner)
    next_task = scheduler.complete_task(task)

    assert next_task is not None
    assert next_task.due_date == (date.today() + timedelta(weeks=1)).isoformat()


def test_complete_nonrecurring_task_returns_none():
    owner = make_owner()
    pet = Pet(name="Buddy", species="Dog", age=3)
    task = make_task("One-off", is_recurring=False)
    pet.add_task(task)
    owner.add_pet(pet)

    scheduler = Scheduler(owner)
    result = scheduler.complete_task(task)

    assert result is None
    assert len(pet.get_tasks()) == 1   # no new task added


def test_complete_task_marks_original_as_done_and_adds_new():
    owner = make_owner()
    pet = Pet(name="Luna", species="Cat", age=2)
    task = make_task("Meds", is_recurring=True, frequency="daily")
    pet.add_task(task)
    owner.add_pet(pet)

    scheduler = Scheduler(owner)
    scheduler.complete_task(task)

    tasks = pet.get_tasks()
    assert tasks[0].is_complete is True
    assert tasks[1].is_complete is False
    assert len(tasks) == 2


# ── Conflict detection ─────────────────────────────────────────────────────────

def test_detect_conflicts_flags_duplicate_times():
    owner = make_owner()
    scheduler = Scheduler(owner)
    tasks = [
        make_task("Walk",    scheduled_time="08:00"),
        make_task("Feeding", scheduled_time="08:00"),
    ]
    warnings = scheduler.detect_conflicts(tasks)
    assert len(warnings) == 1
    assert "08:00" in warnings[0]


def test_detect_conflicts_no_warning_for_unique_times():
    owner = make_owner()
    scheduler = Scheduler(owner)
    tasks = [
        make_task("Walk",    scheduled_time="07:00"),
        make_task("Feeding", scheduled_time="08:00"),
    ]
    assert scheduler.detect_conflicts(tasks) == []


def test_detect_conflicts_ignores_completed_tasks():
    owner = make_owner()
    scheduler = Scheduler(owner)
    completed = make_task("Done Task", scheduled_time="08:00")
    completed.mark_complete()
    pending = make_task("Pending Task", scheduled_time="08:00")

    warnings = scheduler.detect_conflicts([completed, pending])
    assert warnings == []


# ── generate_plan edge cases ───────────────────────────────────────────────────

def test_generate_plan_skips_task_exceeding_available_time():
    owner = make_owner(minutes=20)
    pet = Pet(name="Buddy", species="Dog", age=3)
    pet.add_task(make_task("Short", duration=10, priority=Priority.HIGH))
    pet.add_task(make_task("Long",  duration=60, priority=Priority.HIGH))
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()
    names = [t.name for t in plan]
    assert "Short" in names
    assert "Long" not in names


def test_generate_plan_excludes_completed_tasks():
    owner = make_owner(minutes=60)
    pet = Pet(name="Buddy", species="Dog", age=3)
    done = make_task("Already Done", duration=10, priority=Priority.HIGH)
    done.mark_complete()
    pet.add_task(done)
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()
    assert plan == []
