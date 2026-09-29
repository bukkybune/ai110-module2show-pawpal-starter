"""Tests for the PawPal+ logic layer.

Run from the project root:

    python -m pytest
"""

from datetime import date, time

import pytest

from pawpal_system import COMPLETE, PENDING, CareTask, Owner, Pet, Scheduler

MONDAY = date(2026, 9, 28)
TUESDAY = date(2026, 9, 29)


def make_owner(minutes: int = 120, start: time = time(8, 0)) -> tuple[Owner, Pet]:
    """An owner with one empty pet, the usual starting point for a test."""
    owner = Owner("Jordan", available_minutes=minutes, preferred_start_time=start)
    pet = Pet("Mochi", "dog")
    owner.add_pet(pet)
    return owner, pet


def titles(entries: list[dict]) -> list[str]:
    return [entry["title"] for entry in entries]


def reasons(skipped: list[dict]) -> dict:
    return {item["task"].title: item["reason"] for item in skipped}


# --- Basics --------------------------------------------------------------


def test_mark_complete_changes_task_status():
    """Calling mark_complete() should flip the task out of 'pending'."""
    task = CareTask("t1", "Morning walk", 30, "high")
    assert task.status == PENDING
    assert task.is_complete is False

    task.mark_complete()

    assert task.status == COMPLETE
    assert task.is_complete is True


def test_adding_task_increases_pet_task_count():
    """Each task added to a pet should show up in that pet's task list."""
    pet = Pet("Mochi", "dog")
    assert len(pet.list_tasks()) == 0

    pet.add_task(CareTask("t1", "Breakfast", 10, "high"))
    assert len(pet.list_tasks()) == 1

    pet.add_task(CareTask("t2", "Training", 20, "medium"))
    assert len(pet.list_tasks()) == 2
    assert [task.title for task in pet.list_tasks()] == ["Breakfast", "Training"]


def test_completed_task_is_not_scheduled():
    """A task marked done should be reported as skipped, not given a time slot."""
    owner, pet = make_owner()
    walk = CareTask("t1", "Morning walk", 30, "high")
    pet.add_task(walk)
    pet.add_task(CareTask("t2", "Breakfast", 10, "high"))

    walk.mark_complete(TUESDAY)
    plan = Scheduler().build_household_plan(owner, TUESDAY)

    assert titles(plan["entries"]) == ["Breakfast"]
    assert reasons(plan["skipped"]) == {"Morning walk": "already done"}


def test_completion_is_per_day_so_daily_tasks_come_back():
    """Finishing a daily task today must not cancel it tomorrow."""
    owner, pet = make_owner()
    task = CareTask("t1", "Breakfast", 10, "high", recurrence="daily")
    pet.add_task(task)

    task.mark_complete(MONDAY)

    assert titles(Scheduler().build_household_plan(owner, MONDAY)["entries"]) == []
    assert titles(Scheduler().build_household_plan(owner, TUESDAY)["entries"]) == ["Breakfast"]


# --- 1. Sorting by time --------------------------------------------------


def test_anchored_task_waits_for_its_window():
    """A task with an 'earliest' time should not be pulled forward."""
    owner, pet = make_owner()
    pet.add_task(CareTask("t1", "Vet visit", 30, "medium", earliest=time(14, 0)))
    pet.add_task(CareTask("t2", "Breakfast", 10, "high"))

    entries = Scheduler().build_household_plan(owner, TUESDAY)["entries"]

    assert titles(entries) == ["Breakfast", "Vet visit"]
    assert entries[1]["start_time"] == time(14, 0)


def test_task_that_cannot_finish_by_its_deadline_is_skipped():
    """A window too small for the task is reported, not silently stretched."""
    owner, pet = make_owner(start=time(8, 0))
    pet.add_task(CareTask("t1", "Long groom", 60, "high", earliest=time(9, 0), latest=time(9, 30)))

    plan = Scheduler().build_household_plan(owner, TUESDAY)

    assert plan["entries"] == []
    assert "cannot fit 60 min" in reasons(plan["skipped"])["Long groom"]


def test_skipped_tasks_are_listed_highest_priority_first():
    """The most important casualty should lead the skipped list."""
    owner, pet = make_owner(minutes=15)
    pet.add_task(CareTask("t1", "Nap watch", 40, "low"))
    pet.add_task(CareTask("t2", "Meds", 40, "high"))

    plan = Scheduler().build_household_plan(owner, TUESDAY)

    assert [item["task"].title for item in plan["skipped"]] == ["Meds", "Nap watch"]


# --- 2. Filtering by pet / status ----------------------------------------


def test_only_pets_filter_limits_the_plan():
    """Filtering by pet should leave the other pet's tasks out entirely."""
    owner, mochi = make_owner()
    biscuit = Pet("Biscuit", "cat")
    biscuit.add_task(CareTask("b1", "Litter box", 15, "high"))
    owner.add_pet(biscuit)
    mochi.add_task(CareTask("m1", "Morning walk", 30, "high"))

    plan = Scheduler().build_household_plan(owner, TUESDAY, only_pets=["Biscuit"])

    assert titles(plan["entries"]) == ["Litter box"]
    assert plan["skipped"] == []


def test_min_priority_filter_drops_lower_priority_tasks():
    """A priority floor should exclude anything below it, with a reason."""
    owner, pet = make_owner()
    pet.add_task(CareTask("t1", "Meds", 5, "high"))
    pet.add_task(CareTask("t2", "Brushing", 10, "low"))

    plan = Scheduler().build_household_plan(owner, TUESDAY, min_priority="medium")

    assert titles(plan["entries"]) == ["Meds"]
    assert reasons(plan["skipped"]) == {"Brushing": "below medium priority"}


def test_per_pet_cap_stops_one_pet_taking_the_whole_day():
    """A pet cap should leave budget for the other animal."""
    owner, mochi = make_owner(minutes=200)
    biscuit = Pet("Biscuit", "cat")
    biscuit.add_task(CareTask("b1", "Play", 20, "medium"))
    owner.add_pet(biscuit)
    mochi.add_task(CareTask("m1", "Walk", 30, "high"))
    mochi.add_task(CareTask("m2", "Groom", 30, "high"))

    plan = Scheduler(max_minutes_per_pet=30).build_household_plan(owner, TUESDAY)

    assert titles(plan["entries"]) == ["Walk", "Play"]
    assert "capped at 30 min/day" in reasons(plan["skipped"])["Groom"]


def test_upcoming_returns_only_later_entries():
    """The 'what is left' view should drop slots that have already started."""
    owner, pet = make_owner()
    pet.add_task(CareTask("t1", "Breakfast", 10, "high"))
    pet.add_task(CareTask("t2", "Walk", 30, "medium"))

    scheduler = Scheduler()
    plan = scheduler.build_household_plan(owner, TUESDAY)

    assert titles(scheduler.upcoming(plan, time(8, 5))) == ["Walk"]


# --- 3. Recurring tasks --------------------------------------------------


def test_weekly_task_runs_only_on_its_weekdays():
    """A weekday list should decide the day, not a 7-day count."""
    owner, pet = make_owner()
    pet.add_task(CareTask("t1", "Nail trim", 15, "low", recurrence="weekly", weekdays={"mon"}))

    assert titles(Scheduler().build_household_plan(owner, MONDAY)["entries"]) == ["Nail trim"]
    assert titles(Scheduler().build_household_plan(owner, TUESDAY)["entries"]) == []


def test_interval_recurrence_repeats_every_n_days():
    """An interval task is due on the anchor day and every N days after."""
    task = CareTask(
        "t1", "Flea treatment", 10, "high",
        recurrence="interval", interval_days=30, start_date=date(2026, 9, 1),
    )

    assert task.is_due_today(date(2026, 9, 1)) is True
    assert task.is_due_today(date(2026, 9, 15)) is False
    assert task.is_due_today(date(2026, 10, 1)) is True


def test_missed_recurring_task_is_treated_as_overdue():
    """Skipping yesterday should bump a daily task above its usual rank."""
    task = CareTask(
        "t1", "Meds", 5, "low", recurrence="daily", start_date=date(2026, 9, 1)
    )

    assert task.is_overdue(TUESDAY) is True
    assert task.effective_rank(TUESDAY) > task.priority_rank

    task.mark_complete(MONDAY)
    assert task.is_overdue(TUESDAY) is False


def test_new_task_without_history_is_not_overdue():
    """A task created today should not be reported as already behind."""
    assert CareTask("t1", "Meds", 5, "high", recurrence="daily").is_overdue(TUESDAY) is False


def test_tasks_due_on_looks_ahead():
    """Look-ahead should report tomorrow's workload."""
    owner, pet = make_owner()
    pet.add_task(CareTask("t1", "Nail trim", 15, "low", recurrence="weekly", weekdays={"tue"}))
    pet.add_task(CareTask("t2", "Breakfast", 10, "high", recurrence="daily"))

    due = Scheduler().tasks_due_on(owner, TUESDAY)

    assert sorted(task.title for _, task in due) == ["Breakfast", "Nail trim"]


# --- 4. Conflict detection -----------------------------------------------


def test_two_anchored_tasks_cannot_occupy_the_same_slot():
    """The second task wanting a taken slot is pushed out, and says so."""
    owner, pet = make_owner()
    pet.add_task(
        CareTask("t1", "Vet call", 30, "high", earliest=time(9, 0), latest=time(9, 30))
    )
    pet.add_task(
        CareTask("t2", "Groomer call", 30, "high", earliest=time(9, 0), latest=time(9, 30))
    )

    plan = Scheduler().build_household_plan(owner, TUESDAY)

    assert len(plan["entries"]) == 1
    assert "no free slot before 09:30" in list(reasons(plan["skipped"]).values())[0]


def test_min_gap_pushes_a_task_away_from_its_predecessor():
    """A second dose must wait the required gap after the first."""
    owner, pet = make_owner(minutes=300)
    pet.add_task(CareTask("t1", "Meds AM", 5, "high"))
    pet.add_task(
        CareTask("t2", "Meds PM", 5, "high", min_gap_from="t1", min_gap_minutes=360)
    )

    entries = Scheduler().build_household_plan(owner, TUESDAY)["entries"]

    assert entries[0]["start_time"] == time(8, 0)
    assert entries[1]["start_time"] == time(14, 5)  # 08:05 + 6 hours


def test_avoid_after_forces_a_rest_gap():
    """A walk must wait out a rest period after feeding, not start on its heels."""
    owner, pet = make_owner()
    pet.add_task(CareTask("t1", "Breakfast", 10, "high"))
    pet.add_task(CareTask("t2", "Walk", 20, "high", avoid_after={"t1"}, avoid_after_minutes=30))

    entries = Scheduler().build_household_plan(owner, TUESDAY)["entries"]
    slots = {entry["title"]: entry for entry in entries}

    assert slots["Breakfast"]["end_time"] == time(8, 10)
    assert slots["Walk"]["start_time"] == time(8, 40)  # 08:10 + 30 min rest


def test_rest_gap_fills_with_another_pets_task():
    """The rest period is usable time, not dead time."""
    owner, mochi = make_owner()
    biscuit = Pet("Biscuit", "cat")
    biscuit.add_task(CareTask("b1", "Litter box", 15, "medium"))
    owner.add_pet(biscuit)
    mochi.add_task(CareTask("t1", "Breakfast", 10, "high"))
    mochi.add_task(CareTask("t2", "Walk", 20, "high", avoid_after={"t1"}))

    entries = Scheduler().build_household_plan(owner, TUESDAY)["entries"]

    # Litter box slots into the gap while Mochi digests.
    assert titles(entries) == ["Breakfast", "Litter box", "Walk"]


def test_over_commitment_is_warned_about_up_front():
    """Asking for more than the day holds should raise a warning."""
    owner, pet = make_owner(minutes=30)
    pet.add_task(CareTask("t1", "Walk", 30, "high"))
    pet.add_task(CareTask("t2", "Groom", 45, "low"))

    plan = Scheduler().build_household_plan(owner, TUESDAY)

    assert any("over-committed by" in warning for warning in plan["warnings"])


def test_buffer_is_counted_against_the_budget():
    """Gaps are real time, so selection must not approve a set that overruns."""
    owner, pet = make_owner(minutes=25)
    pet.add_task(CareTask("t1", "A", 10, "high"))
    pet.add_task(CareTask("t2", "B", 10, "high"))

    plan = Scheduler(buffer_minutes=10).build_household_plan(owner, TUESDAY)

    assert len(plan["entries"]) == 1  # 10 + 10 gap + 10 = 30 > 25


# --- Public sorting / filtering helpers ----------------------------------


def test_sort_by_time_orders_timed_tasks_and_puts_untimed_last():
    """sort_by_time should read the clock, not the insertion order."""
    tasks = [
        CareTask("t1", "Evening meds", 5, "high", earliest=time(18, 0)),
        CareTask("t2", "Grooming", 30, "low"),  # no time at all
        CareTask("t3", "Breakfast", 10, "high", earliest=time(7, 30)),
        CareTask("t4", "Vet", 30, "high", earliest=time(9, 15)),
    ]

    ordered = Scheduler().sort_by_time(tasks)

    assert [task.title for task in ordered] == [
        "Breakfast", "Vet", "Evening meds", "Grooming"
    ]


def test_times_can_be_given_as_hh_mm_strings():
    """'08:30' should be accepted and stored as a real time."""
    task = CareTask("t1", "Meds", 5, "high", earliest="08:30", latest="09:00")

    assert task.earliest == time(8, 30)
    assert task.latest == time(9, 0)

    with pytest.raises(ValueError):
        CareTask("t2", "Meds", 5, "high", earliest="half past eight")


def test_filter_tasks_by_pet_and_status():
    """Filtering should narrow by animal and by whether the task is done."""
    owner, mochi = make_owner()
    biscuit = Pet("Biscuit", "cat")
    owner.add_pet(biscuit)
    mochi.add_task(CareTask("m1", "Walk", 30, "high"))
    mochi.add_task(CareTask("m2", "Breakfast", 10, "high"))
    biscuit.add_task(CareTask("b1", "Litter box", 15, "medium"))

    mochi.mark_task_complete("m2", TUESDAY)
    scheduler = Scheduler()

    by_pet = scheduler.filter_tasks(owner, pet_name="Biscuit", day=TUESDAY)
    assert [task.title for _, task in by_pet] == ["Litter box"]

    pending = scheduler.filter_tasks(owner, status=PENDING, day=TUESDAY)
    assert sorted(task.title for _, task in pending) == ["Litter box", "Walk"]

    done = scheduler.filter_tasks(owner, status=COMPLETE, day=TUESDAY)
    assert [task.title for _, task in done] == ["Breakfast"]


# --- Recurring task chains -----------------------------------------------


def test_completing_a_daily_chain_creates_tomorrows_task():
    """A dated daily task should queue up its own successor."""
    _, pet = make_owner()
    pet.add_task(CareTask("m1", "Breakfast", 10, "high", recurrence="daily", due_date=MONDAY))

    follow_up = pet.mark_task_complete("m1", MONDAY)

    assert follow_up is not None
    assert follow_up.due_date == TUESDAY  # Monday + 1 day
    assert follow_up.is_complete_on(TUESDAY) is False
    assert len(pet.list_tasks()) == 2


def test_weekly_chain_jumps_to_the_next_wanted_weekday():
    """A Saturday task completed on Saturday comes back the next Saturday."""
    saturday = date(2026, 10, 3)
    task = CareTask(
        "m1", "Nail trim", 15, "low",
        recurrence="weekly", weekdays={"sat"}, due_date=saturday,
    )

    assert task.next_due_date(saturday) == date(2026, 10, 10)


def test_pinned_task_is_only_due_on_its_own_day():
    """A dated task must not also fire on the rule-based schedule."""
    task = CareTask("m1", "Breakfast", 10, "high", recurrence="daily", due_date=MONDAY)

    assert task.is_due_today(MONDAY) is True
    assert task.is_due_today(TUESDAY) is False


def test_rule_based_task_does_not_spawn_duplicates():
    """Completing an undated recurring task must not add a second copy."""
    _, pet = make_owner()
    pet.add_task(CareTask("m1", "Breakfast", 10, "high", recurrence="daily"))

    assert pet.mark_task_complete("m1", MONDAY) is None
    assert len(pet.list_tasks()) == 1


# --- Same-time conflict warnings -----------------------------------------


def test_two_tasks_at_the_same_time_produce_a_warning_not_a_crash():
    """Overlapping requests should be reported and the plan still built."""
    owner, mochi = make_owner()
    biscuit = Pet("Biscuit", "cat")
    owner.add_pet(biscuit)
    mochi.add_task(CareTask("m1", "Vet call", 30, "high", earliest="09:00"))
    biscuit.add_task(CareTask("b1", "Groomer call", 30, "high", earliest="09:00"))

    conflicts = Scheduler().detect_conflicts(owner, TUESDAY)
    plan = Scheduler().build_household_plan(owner, TUESDAY)

    assert len(conflicts) == 1
    assert "Vet call (Mochi)" in conflicts[0] and "Groomer call (Biscuit)" in conflicts[0]
    assert any("clash:" in warning for warning in plan["warnings"])
    assert len(plan["entries"]) == 2  # both still scheduled, one shifted later


def test_tasks_that_merely_touch_are_not_a_conflict():
    """Back-to-back requests are fine; only genuine overlap is reported."""
    owner, pet = make_owner()
    pet.add_task(CareTask("t1", "First", 30, "high", earliest="09:00"))
    pet.add_task(CareTask("t2", "Second", 30, "high", earliest="09:30"))

    assert Scheduler().detect_conflicts(owner, TUESDAY) == []


# --- Validation ----------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"priority": "urgent"},
        {"duration_minutes": 0},
        {"recurrence": "hourly"},
        {"weekdays": {"funday"}},
        {"recurrence": "interval"},  # missing interval_days
        {"earliest": time(10, 0), "latest": time(9, 0)},
        {"min_gap_minutes": -5},
    ],
)
def test_invalid_task_is_rejected(kwargs):
    """Bad task data should fail loudly at construction."""
    defaults = {"task_id": "t1", "title": "Task", "duration_minutes": 10, "priority": "high"}
    with pytest.raises(ValueError):
        CareTask(**{**defaults, **kwargs})
