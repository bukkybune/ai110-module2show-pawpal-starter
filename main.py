from pawpal_system import Owner, Pet, Task, Priority, Scheduler

# --- Setup ---
owner = Owner(name="Dorcas", available_minutes_per_day=90, preferred_time_of_day="morning")

dog = Pet(name="Buddy", species="Dog", age=3)
cat = Pet(name="Luna", species="Cat", age=5, special_needs="Needs medication after meals")

dog.add_task(Task(name="Morning Walk", category="exercise",  duration_minutes=30, priority=Priority.HIGH,   is_recurring=True, frequency="daily",  scheduled_time="07:00"))
dog.add_task(Task(name="Feeding",      category="feeding",   duration_minutes=10, priority=Priority.HIGH,   is_recurring=True, frequency="daily",  scheduled_time="08:00"))
dog.add_task(Task(name="Bath Time",    category="grooming",  duration_minutes=40, priority=Priority.LOW,    is_recurring=True, frequency="weekly", scheduled_time="14:00"))

# Medication and Brushing intentionally share "08:00" to trigger a conflict
cat.add_task(Task(name="Medication",   category="meds",      duration_minutes=5,  priority=Priority.HIGH,   is_recurring=True, frequency="daily",  scheduled_time="08:00", notes="Give with food"))
cat.add_task(Task(name="Brushing",     category="grooming",  duration_minutes=15, priority=Priority.MEDIUM, is_recurring=True, frequency="daily",  scheduled_time="10:00"))

owner.add_pet(dog)
owner.add_pet(cat)

scheduler = Scheduler(owner)

# ── Conflict detection ────────────────────────────────────
print("=" * 50)
print("  CONFLICT CHECK")
print("=" * 50)
conflicts = scheduler.detect_conflicts(scheduler.get_all_tasks())
if conflicts:
    for warning in conflicts:
        print(f"  {warning}")
else:
    print("  No conflicts found.")

# ── Before completion ─────────────────────────────────────
print("=" * 50)
print("  BEFORE — Buddy's tasks")
print("=" * 50)
for t in scheduler.filter_by_pet("Buddy"):
    print(f"  {t.get_summary()}")

# ── Complete two tasks and check recurrence ───────────────
morning_walk = dog.get_tasks()[0]   # daily
bath_time    = dog.get_tasks()[2]   # weekly

next_walk = scheduler.complete_task(morning_walk)
next_bath = scheduler.complete_task(bath_time)

print("\n" + "=" * 50)
print("  AFTER completing 'Morning Walk' (daily) and 'Bath Time' (weekly)")
print("=" * 50)
for t in scheduler.filter_by_pet("Buddy"):
    print(f"  {t.get_summary()}")

print("\n" + "=" * 50)
print("  NEW occurrences created")
print("=" * 50)
print(f"  Next walk : {next_walk.get_summary()}")
print(f"  Next bath : {next_bath.get_summary()}")

# ── Final schedule reflects new tasks ────────────────────
print("\n" + "=" * 50)
print("       TODAY'S PAWPAL+ SCHEDULE")
print("=" * 50)
plan = scheduler.generate_plan()
time_used = sum(t.duration_minutes for t in plan)
for i, t in enumerate(plan, 1):
    print(f"  {i}. {t.get_summary()}")
print("-" * 50)
print(f"  Scheduled: {time_used} min | Remaining: {owner.available_minutes_per_day - time_used} min")
print("=" * 50)
print(scheduler.explain_reasoning())
