"""Terminal testing ground for the PawPal+ logic layer.

Builds an owner with two pets, deliberately adds the tasks out of order, then
shows the sorting, filtering, conflict and recurrence logic working:

    python main.py

This is scratch code for checking the logic by eye, not the real test suite.
"""

from datetime import date, time

from pawpal_system import COMPLETE, PENDING, CareTask, Owner, Pet, Scheduler


def banner(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def build_household() -> Owner:
    """One owner, two pets, tasks added deliberately out of order."""
    owner = Owner(name="Jordan", available_minutes=180, preferred_start_time=time(8, 0))

    mochi = Pet(name="Mochi", species="dog", breed="Corgi", age_years=3)
    # Added late in the day first, and the morning tasks last, on purpose.
    mochi.add_task(CareTask("m4", "Grooming", 45, "low"))
    mochi.add_task(CareTask("m6", "Vet call", 30, "high", earliest="09:00"))
    mochi.add_task(CareTask("m5", "Nail trim", 15, "low", recurrence="weekly", weekdays={"sat"}))
    # A brisk walk straight after eating risks bloat in a deep-chested dog.
    mochi.add_task(CareTask("m1", "Morning walk", 30, "high", avoid_after={"m2"}))
    mochi.add_task(CareTask("m3", "Training", 20, "medium"))
    # Dated daily task: completing it spawns tomorrow's copy.
    mochi.add_task(
        CareTask("m2", "Breakfast", 10, "high", recurrence="daily", due_date=date.today())
    )

    biscuit = Pet(name="Biscuit", species="cat", breed="Tabby", age_years=7)
    biscuit.add_task(CareTask("b3", "Play session", 25, "low"))
    # Groomer rings at the same time as the vet: a conflict to warn about.
    biscuit.add_task(CareTask("b5", "Groomer call", 20, "high", earliest="09:00"))
    biscuit.add_task(CareTask("b2", "Litter box", 15, "medium"))
    # Morning dose has to land with breakfast, evening dose 6 hours later.
    biscuit.add_task(
        CareTask("b1", "Meds", 5, "high", notes="with food", earliest="08:00", latest="09:00")
    )
    biscuit.add_task(
        CareTask("b4", "Meds (evening)", 5, "high", min_gap_from="b1", min_gap_minutes=360)
    )

    owner.add_pet(mochi)
    owner.add_pet(biscuit)
    return owner


def show_sorting(owner: Owner, scheduler: Scheduler) -> None:
    """Prove sort_by_time reorders what was entered in a jumble."""
    tasks = [task for pet in owner.pets for task in pet.list_tasks()]

    banner("1. Sorting — as entered, then sorted by time")
    print("As entered:")
    for task in tasks:
        print(f"  {task.summary()}")

    print("\nSorted by time (untimed tasks last):")
    for task in scheduler.sort_by_time(tasks):
        when = f"{task.earliest:%H:%M}" if task.earliest else "  --  "
        print(f"  {when}  {task.title}")


def show_filtering(owner: Owner, scheduler: Scheduler, today: date) -> None:
    """Prove filter_tasks narrows by pet and by completion status."""
    banner("2. Filtering — by pet, then by status")

    for pet_name in ("Mochi", "Biscuit"):
        found = scheduler.filter_tasks(owner, pet_name=pet_name, day=today)
        print(f"  {pet_name}: {', '.join(task.title for _, task in found)}")

    mochi = owner.get_pet("Mochi")
    mochi.mark_task_complete("m3", today)  # Training is done already
    print("\n  (marked Training complete)")

    for status in (PENDING, COMPLETE):
        found = scheduler.filter_tasks(owner, status=status, day=today)
        print(f"  {status}: {', '.join(task.title for _, task in found)}")


def show_conflicts(owner: Owner, scheduler: Scheduler, today: date) -> None:
    """Prove two tasks wanting one slot warn instead of crashing."""
    banner("3. Conflict detection")

    conflicts = scheduler.detect_conflicts(owner, today)
    if not conflicts:
        print("  no clashes found")
    for warning in conflicts:
        print(f"  ! {warning}")


def show_plan(owner: Owner, scheduler: Scheduler, today: date) -> None:
    """Print the day as one timeline."""
    banner(f"4. TODAY'S SCHEDULE — {today.strftime('%A, %d %B %Y')}")
    print(
        f"{owner.name} has {owner.available_minutes} minutes "
        f"from {owner.preferred_start_time.strftime('%H:%M')}, "
        f"across {len(owner.pets)} pets "
        f"({', '.join(pet.name for pet in owner.pets)}).\n"
    )

    plan = scheduler.build_household_plan(owner, today)
    for warning in plan["warnings"]:
        print(f"  ! {warning}")

    print("-" * 70)
    for entry in plan["entries"]:
        start = entry["start_time"].strftime("%H:%M")
        end = entry["end_time"].strftime("%H:%M")
        print(
            f"  {start} - {end}  {entry['title']:<15}{entry['pet'].name:<9}"
            f"{entry['scheduled_minutes']:>3} min  [{entry['priority']}]"
        )
        if entry["notes"]:
            print(f"{'':>17}note: {entry['notes']}")

    if plan["skipped"]:
        print("\n  Not today:")
        for item in plan["skipped"]:
            print(f"    {item['task'].title} ({item['pet'].name}) — {item['reason']}")

    booked = sum(entry["scheduled_minutes"] for entry in plan["entries"])
    used = plan["minutes_used"]
    print("\n" + "-" * 70)
    print(
        f"  {used} of {owner.available_minutes} minutes used "
        f"({booked} on tasks, {used - booked} on gaps), "
        f"{owner.available_minutes - used} to spare."
    )


def show_recurrence(owner: Owner, today: date) -> None:
    """Prove completing a dated recurring task queues up the next one."""
    banner("5. Recurrence — completing a daily task rolls it forward")

    mochi = owner.get_pet("Mochi")
    before = len(mochi.list_tasks())
    follow_up = mochi.mark_task_complete("m2", today)

    print(f"  completed Breakfast for {today.isoformat()}")
    if follow_up:
        print(f"  created   {follow_up.title} due {follow_up.due_date.isoformat()} "
              f"(id {follow_up.task_id})")
    print(f"  task count {before} -> {len(mochi.list_tasks())}")

    print("\n  Tomorrow's workload:")
    tomorrow = follow_up.due_date if follow_up else today
    for pet, task in Scheduler().tasks_due_on(owner, tomorrow):
        print(f"    {pet.name}: {task.title}")


def main() -> None:
    owner = build_household()
    scheduler = Scheduler(buffer_minutes=5)
    today = date.today()

    show_sorting(owner, scheduler)
    show_filtering(owner, scheduler, today)
    show_conflicts(owner, scheduler, today)
    show_plan(owner, scheduler, today)
    show_recurrence(owner, today)
    print()


if __name__ == "__main__":
    main()
