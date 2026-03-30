from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum


class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class Task:
    name: str
    category: str
    duration_minutes: int
    priority: Priority
    is_recurring: bool = False
    frequency: str = "daily"   # "daily" or "weekly"
    notes: str = ""
    is_complete: bool = False
    scheduled_time: str = ""   # "HH:MM" format, e.g. "08:00"
    due_date: str = ""         # "YYYY-MM-DD" format

    def mark_complete(self):
        """Mark this task as completed."""
        self.is_complete = True

    def get_summary(self) -> str:
        """Return a formatted one-line summary of the task."""
        status = "Done" if self.is_complete else "Pending"
        recurrence = self.frequency.capitalize() if self.is_recurring else "Once"
        due = f", due {self.due_date}" if self.due_date else ""
        return f"[{self.priority.name}] {self.name} ({self.duration_minutes} min, {recurrence}{due}, {status})"

    def is_schedulable(self, remaining_minutes: int) -> bool:
        """Return True if the task is incomplete and fits within the remaining time."""
        return not self.is_complete and self.duration_minutes <= remaining_minutes


@dataclass
class Pet:
    name: str
    species: str
    age: int
    special_needs: str = ""
    tasks: list = field(default_factory=list)

    def add_task(self, task: Task):
        """Add a care task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_name: str):
        """Remove a task from this pet's task list by name."""
        self.tasks = [t for t in self.tasks if t.name != task_name]

    def get_tasks(self) -> list:
        """Return all tasks assigned to this pet."""
        return self.tasks

    def get_profile(self) -> str:
        """Return a formatted string with this pet's basic info."""
        profile = f"{self.name} ({self.species}, age {self.age})"
        if self.special_needs:
            profile += f" — Special needs: {self.special_needs}"
        return profile


@dataclass
class Owner:
    name: str
    available_minutes_per_day: int
    preferred_time_of_day: str = "morning"
    notes: str = ""
    pets: list = field(default_factory=list)

    def add_pet(self, pet: Pet):
        """Add a pet to this owner's list of pets."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str):
        """Remove a pet from this owner's list by name."""
        self.pets = [p for p in self.pets if p.name != pet_name]

    def get_all_tasks(self) -> list:
        """Return a flat list of all tasks across all of the owner's pets."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks

    def get_available_time(self) -> int:
        """Return the total minutes the owner has available today."""
        return self.available_minutes_per_day


class Scheduler:
    def __init__(self, owner: Owner):
        self.owner = owner
        self.skipped = []

    def get_all_tasks(self) -> list:
        """Retrieve all tasks from the owner's pets."""
        return self.owner.get_all_tasks()

    def sort_by_priority(self, tasks: list) -> list:
        """Return tasks sorted from highest to lowest priority."""
        return sorted(tasks, key=lambda t: t.priority.value)

    def filter_by_priority(self, tasks: list, max_priority: Priority) -> list:
        """Return only tasks at or above the given priority level."""
        return [t for t in tasks if t.priority.value <= max_priority.value]

    def sort_by_time(self, tasks: list) -> list:
        """Return tasks sorted chronologically by their scheduled_time field.

        Expects scheduled_time in "HH:MM" format. Tasks with no scheduled_time
        are sorted to the end of the list using the sentinel value "99:99".
        Does not modify the original list.
        """
        return sorted(tasks, key=lambda t: t.scheduled_time if t.scheduled_time else "99:99")

    def filter_by_status(self, tasks: list, completed: bool) -> list:
        """Return tasks matching the given completion status.

        Pass completed=True to retrieve finished tasks, or completed=False
        to retrieve tasks that are still pending. Returns an empty list if
        no tasks match.
        """
        return [t for t in tasks if t.is_complete == completed]

    def filter_by_pet(self, pet_name: str) -> list:
        """Return all tasks belonging to the named pet.

        The name match is case-insensitive. Returns an empty list if no pet
        with that name is found rather than raising an exception.
        """
        for pet in self.owner.pets:
            if pet.name.lower() == pet_name.lower():
                return pet.get_tasks()
        return []

    def detect_conflicts(self, tasks: list) -> list:
        """Return warning strings for any pending tasks that share the same scheduled_time.

        Uses exact HH:MM matching — overlapping durations are not detected.
        Tasks with no scheduled_time or that are already complete are ignored.
        Returns an empty list if no conflicts are found.
        """
        buckets: defaultdict = defaultdict(list)
        for task in tasks:
            if task.scheduled_time and not task.is_complete:
                buckets[task.scheduled_time].append(task)

        warnings = []
        for time_slot, conflicting in buckets.items():
            if len(conflicting) > 1:
                names = ", ".join(t.name for t in conflicting)
                warnings.append(f"WARNING: conflict at {time_slot} — {names}")
        return warnings

    def complete_task(self, task: Task) -> "Task | None":
        """Mark a task complete and, if recurring, add the next occurrence to its pet.

        Returns the newly created next-occurrence Task, or None if not recurring.
        """
        task.mark_complete()

        if not task.is_recurring:
            return None

        delta = timedelta(days=1) if task.frequency == "daily" else timedelta(weeks=1)
        next_due = (date.today() + delta).isoformat()

        next_task = Task(
            name=task.name,
            category=task.category,
            duration_minutes=task.duration_minutes,
            priority=task.priority,
            is_recurring=task.is_recurring,
            frequency=task.frequency,
            notes=task.notes,
            scheduled_time=task.scheduled_time,
            due_date=next_due,
        )

        for pet in self.owner.pets:
            if task in pet.get_tasks():
                pet.add_task(next_task)
                break

        return next_task

    def generate_plan(self) -> list:
        """Build a prioritized daily plan that fits within the owner's available time."""
        tasks = self.sort_by_priority(self.get_all_tasks())
        remaining = self.owner.get_available_time()
        plan = []
        self.skipped = []

        for task in tasks:
            if task.is_schedulable(remaining):
                plan.append(task)
                remaining -= task.duration_minutes
            else:
                self.skipped.append(task)

        return plan

    def explain_reasoning(self) -> str:
        """Explain which tasks were skipped and why."""
        if not self.skipped:
            return "All tasks fit within the available time."
        lines = ["Skipped tasks (not enough time remaining):"]
        for task in self.skipped:
            lines.append(f"  - {task.name} ({task.duration_minutes} min)")
        return "\n".join(lines)
