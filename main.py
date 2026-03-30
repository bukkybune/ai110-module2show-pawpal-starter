from pawpal_system import Owner, Pet, Task, Priority, Scheduler

# --- Setup ---
owner = Owner(name="Dorcas", available_minutes_per_day=90, preferred_time_of_day="morning")

dog = Pet(name="Buddy", species="Dog", age=3)
cat = Pet(name="Luna", species="Cat", age=5, special_needs="Needs medication after meals")

# --- Tasks for Buddy ---
dog.add_task(Task(name="Morning Walk", category="exercise", duration_minutes=30, priority=Priority.HIGH, is_recurring=True))
dog.add_task(Task(name="Feeding", category="feeding", duration_minutes=10, priority=Priority.HIGH, is_recurring=True))
dog.add_task(Task(name="Bath Time", category="grooming", duration_minutes=40, priority=Priority.LOW))

# --- Tasks for Luna ---
cat.add_task(Task(name="Medication", category="meds", duration_minutes=5, priority=Priority.HIGH, is_recurring=True, notes="Give with food"))
cat.add_task(Task(name="Brushing", category="grooming", duration_minutes=15, priority=Priority.MEDIUM, is_recurring=True))

# --- Register pets with owner ---
owner.add_pet(dog)
owner.add_pet(cat)

# --- Run scheduler ---
scheduler = Scheduler(owner)
plan = scheduler.generate_plan()

# --- Print today's schedule ---
print("=" * 40)
print("       TODAY'S PAWPAL+ SCHEDULE")
print("=" * 40)
print(f"Owner : {owner.name}")
print(f"Available time: {owner.available_minutes_per_day} min")
print(f"Pets  : {', '.join(p.name for p in owner.pets)}")
print("-" * 40)

time_used = 0
for i, task in enumerate(plan, 1):
    print(f"{i}. {task.get_summary()}")
    time_used += task.duration_minutes

print("-" * 40)
print(f"Total time scheduled: {time_used} min")
print(f"Time remaining      : {owner.available_minutes_per_day - time_used} min")
print("=" * 40)
print(scheduler.explain_reasoning())
