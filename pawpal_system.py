from dataclasses import dataclass, field
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
    notes: str = ""
    is_complete: bool = False

    def mark_complete(self):
        """Mark this task as completed."""
        self.is_complete = True

    def get_summary(self) -> str:
        """Return a formatted one-line summary of the task."""
        status = "Done" if self.is_complete else "Pending"
        recurrence = "Daily" if self.is_recurring else "Once"
        return f"[{self.priority.name}] {self.name} ({self.duration_minutes} min, {recurrence}, {status})"

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
