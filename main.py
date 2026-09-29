"""Terminal testing ground for the PawPal+ logic layer.

Builds an owner with two pets, gives them care tasks of different lengths and
priorities, and prints today's schedule:

    python main.py

This is scratch code for checking the logic by eye, not the real test suite.
"""

from datetime import date, time

from pawpal_system import CareTask, Owner, Pet, Scheduler


def build_household() -> Owner:
    """One owner, two pets, seven tasks of varying length and priority."""
    owner = Owner(name="Jordan", available_minutes=120, preferred_start_time=time(8, 0))

    mochi = Pet(name="Mochi", species="dog", breed="Corgi", age_years=3)
    mochi.add_task(CareTask("m1", "Morning walk", 30, "high"))
    mochi.add_task(CareTask("m2", "Breakfast", 10, "high"))
    mochi.add_task(CareTask("m3", "Training", 20, "medium"))
    mochi.add_task(CareTask("m4", "Grooming", 45, "low"))

    biscuit = Pet(name="Biscuit", species="cat", breed="Tabby", age_years=7)
    biscuit.add_task(CareTask("b1", "Meds", 5, "high", notes="with food"))
    biscuit.add_task(CareTask("b2", "Litter box", 15, "medium"))
    biscuit.add_task(CareTask("b3", "Play session", 25, "low"))

    owner.add_pet(mochi)
    owner.add_pet(biscuit)
    return owner


def print_plan(plan: dict) -> int:
    """Print the day as one timeline. Returns the minutes booked."""
    print("-" * 70)
    if not plan["entries"]:
        print("  nothing fits in the time available")

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

    return sum(entry["scheduled_minutes"] for entry in plan["entries"])


def main() -> None:
    owner = build_household()
    scheduler = Scheduler(buffer_minutes=5)
    today = date.today()

    print("=" * 70)
    print(f"TODAY'S SCHEDULE — {today.strftime('%A, %d %B %Y')}")
    print("=" * 70)
    print(
        f"{owner.name} has {owner.available_minutes} minutes "
        f"from {owner.preferred_start_time.strftime('%H:%M')}, "
        f"across {len(owner.pets)} pets "
        f"({', '.join(pet.name for pet in owner.pets)}).\n"
    )

    # One timeline for the whole household: every pet's tasks compete for the
    # same budget, so priority decides, not which pet was added first.
    plan = scheduler.build_household_plan(owner, today)
    booked = print_plan(plan)

    print("\n" + "=" * 70)
    print(
        f"{booked} of {owner.available_minutes} minutes planned, "
        f"{owner.available_minutes - booked} to spare."
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
