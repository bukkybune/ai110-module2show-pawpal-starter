"""PawPal+ logic layer.

Backend classes for the pet care planning assistant. Mirrors diagrams/uml.mmd.
Keep the two in sync as the design changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

# Higher number wins when sorting. Keeping the ordering in one place means the
# scheduler never has to hardcode a string comparison.
PRIORITY_ORDER = {"low": 1, "medium": 2, "high": 3}

VALID_RECURRENCE = {"daily", "weekly"}

PENDING = "pending"
COMPLETE = "complete"
VALID_STATUS = {PENDING, COMPLETE}

# A partial task shorter than this is not worth scheduling.
MIN_PARTIAL_MINUTES = 5

# Fields a caller is allowed to change after a task is created.
EDITABLE_TASK_FIELDS = {
    "title",
    "duration_minutes",
    "priority",
    "recurrence",
    "notes",
    "start_date",
    "status",
}


@dataclass
class CareTask:
    """A single unit of pet care work (walk, feeding, meds, grooming...)."""

    task_id: str
    title: str
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"
    recurrence: str | None = None  # "daily" | "weekly" | None
    notes: str | None = None
    start_date: date | None = None  # anchor for weekly recurrence
    status: str = PENDING  # "pending" | "complete"

    def __post_init__(self) -> None:
        """Normalize and validate the fields the scheduler depends on."""
        self.priority = self.priority.strip().lower()
        if self.priority not in PRIORITY_ORDER:
            raise ValueError(
                f"priority must be one of {sorted(PRIORITY_ORDER)}, got {self.priority!r}"
            )

        if self.recurrence is not None:
            self.recurrence = self.recurrence.strip().lower()
            if self.recurrence not in VALID_RECURRENCE:
                raise ValueError(
                    f"recurrence must be one of {sorted(VALID_RECURRENCE)} or None, "
                    f"got {self.recurrence!r}"
                )

        if self.duration_minutes <= 0:
            raise ValueError(f"duration_minutes must be positive, got {self.duration_minutes}")

        self.status = self.status.strip().lower()
        if self.status not in VALID_STATUS:
            raise ValueError(
                f"status must be one of {sorted(VALID_STATUS)}, got {self.status!r}"
            )

    @property
    def priority_rank(self) -> int:
        """Numeric priority, so tasks can be sorted without string comparisons."""
        return PRIORITY_ORDER[self.priority]

    @property
    def is_complete(self) -> bool:
        """True once this task has been marked done."""
        return self.status == COMPLETE

    def mark_complete(self) -> None:
        """Mark this task done for the day."""
        self.status = COMPLETE

    def fits_in(self, remaining_minutes: int) -> bool:
        """Return True if this task can be completed within the time left."""
        return self.duration_minutes <= remaining_minutes

    def is_due_today(self, day: date) -> bool:
        """Return True if this task should be scheduled on the given day."""
        if self.recurrence is None or self.recurrence == "daily":
            return True

        # Weekly: due every seventh day counting from start_date. With no
        # start_date there is no anchor to count from, so treat it as due.
        if self.start_date is None:
            return True
        if day < self.start_date:
            return False
        return (day - self.start_date).days % 7 == 0

    def summary(self) -> str:
        """Return a one-line display form, with notes appended when present."""
        line = f"{self.title} ({self.duration_minutes} min) [{self.priority}]"
        return f"{line} - {self.notes}" if self.notes else line


@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str  # "dog" | "cat" | "other"
    breed: str | None = None
    age_years: int | None = None
    tasks: list[CareTask] = field(default_factory=list)

    def add_task(self, task: CareTask) -> None:
        """Attach a care task to this pet, rejecting a duplicate task id."""
        # Ids must be unique, otherwise remove_task and update_task would
        # silently act on whichever copy happened to come first.
        if any(existing.task_id == task.task_id for existing in self.tasks):
            raise ValueError(f"{self.name} already has a task with id {task.task_id!r}")
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by id. Return True if a task was removed."""
        for index, task in enumerate(self.tasks):
            if task.task_id == task_id:
                del self.tasks[index]
                return True
        return False

    def update_task(self, task_id: str, fields: dict) -> bool:
        """Update fields on a task by id. Return True if a task was updated."""
        unknown = set(fields) - EDITABLE_TASK_FIELDS
        if unknown:
            raise ValueError(f"cannot update unknown field(s): {sorted(unknown)}")

        task = self._find_task(task_id)
        if task is None:
            return False

        original = {name: getattr(task, name) for name in fields}
        for name, value in fields.items():
            setattr(task, name, value)

        # Re-validate, so an edit cannot leave the task in a state the
        # scheduler would choke on.
        try:
            task.__post_init__()
        except ValueError:
            for name, value in original.items():  # leave the task as we found it
                setattr(task, name, value)
            raise
        return True

    def list_tasks(self) -> list[CareTask]:
        """Return this pet's tasks (a copy, so callers cannot mutate the list)."""
        return list(self.tasks)

    def _find_task(self, task_id: str) -> CareTask | None:
        """Return the task with this id, or None if the pet does not have it."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None


@dataclass
class Owner:
    """The person doing the care, and the constraints on their day."""

    name: str
    available_minutes: int
    preferred_start_time: time
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Attach a pet to this owner, rejecting a duplicate name."""
        if any(existing.name.lower() == pet.name.lower() for existing in self.pets):
            raise ValueError(f"{self.name} already has a pet named {pet.name!r}")
        self.pets.append(pet)

    def get_pet(self, name: str) -> Pet | None:
        """Look up one of this owner's pets by name (case-insensitive)."""
        for pet in self.pets:
            if pet.name.lower() == name.strip().lower():
                return pet
        return None


@dataclass
class Scheduler:
    """Builds a daily plan from a pet's tasks and an owner's constraints.

    This is the only class with real scheduling behavior. The private helpers
    exist so each decision (ordering, selection, timing) can be tested alone.
    """

    allow_partial: bool = False  # may a task be shortened to fit?
    buffer_minutes: int = 0  # gap between consecutive tasks

    def build_plan(self, owner: Owner, pet: Pet, plan_date: date) -> dict:
        """Return the plan for one pet on `plan_date`."""
        items = [(pet, task) for task in pet.list_tasks()]
        return self._plan_items(items, owner, plan_date)

    def build_household_plan(self, owner: Owner, plan_date: date) -> dict:
        """Return one plan covering every pet the owner has."""
        # All the pets' tasks compete for the same budget on a single timeline,
        # so a high-priority task beats a low-priority one no matter which
        # animal it belongs to. Planning pets one at a time instead would let
        # the first pet's low-priority tasks crowd out the second pet's urgent
        # ones.
        items = [(pet, task) for pet in owner.pets for task in pet.list_tasks()]
        return self._plan_items(items, owner, plan_date)

    def _plan_items(
        self, items: list[tuple[Pet, CareTask]], owner: Owner, plan_date: date
    ) -> dict:
        """Shared body of build_plan and build_household_plan."""
        due, not_due = [], []
        for pet, task in items:
            if task.is_due_today(plan_date):
                due.append((pet, task))
            else:
                not_due.append(
                    {
                        "pet": pet,
                        "task": task,
                        "reason": f"not due on {plan_date.isoformat()} ({task.recurrence})",
                    }
                )

        ordered = self._sort_tasks(due)
        selected, skipped = self._select_tasks(ordered, owner.available_minutes)
        entries = self._assign_times(selected, owner.preferred_start_time)

        return {
            "plan_date": plan_date,
            "entries": entries,  # scheduled, in clock order
            "skipped": not_due + skipped,  # dicts of (pet, task, reason)
        }

    def explain(self, plan: dict) -> str:
        """Describe why the plan looks the way it does, including what was cut."""
        entries = plan["entries"]
        skipped = plan["skipped"]
        lines = [f"Plan for {plan['plan_date'].isoformat()}"]

        # Only name the pet when the plan covers more than one, otherwise it is
        # noise on every line.
        names = {entry["pet"].name for entry in entries}
        names |= {item["pet"].name for item in skipped}
        show_pet = len(names) > 1

        def label(pet: Pet, title: str) -> str:
            """Add the pet's name to a task title when the plan needs it."""
            return f"{title} for {pet.name}" if show_pet else title

        if not entries:
            lines.append("Nothing could be scheduled in the time available.")
        else:
            booked = sum(entry["scheduled_minutes"] for entry in entries)
            lines.append(
                f"Scheduled {len(entries)} task(s) using {booked} minutes, "
                "ordered by priority first and shorter tasks first within a priority."
            )
            for entry in entries:
                note = f" - {entry['notes']}" if entry["notes"] else ""
                lines.append(
                    f"  {entry['start_time'].strftime('%H:%M')} - "
                    f"{entry['end_time'].strftime('%H:%M')}  "
                    f"{label(entry['pet'], entry['title'])} "
                    f"({entry['reason']}){note}"
                )

        if skipped:
            lines.append(f"Left out {len(skipped)} task(s):")
            for item in skipped:
                lines.append(f"  {label(item['pet'], item['task'].title)}: {item['reason']}")

        return "\n".join(lines)

    def _sort_tasks(
        self, items: list[tuple[Pet, CareTask]]
    ) -> list[tuple[Pet, CareTask]]:
        """Order (pet, task) pairs by priority, then by shortest duration."""
        # Sorting pairs rather than bare tasks is what lets tasks from
        # different pets compete against each other on one timeline.
        return sorted(
            items, key=lambda item: (-item[1].priority_rank, item[1].duration_minutes)
        )

    def _select_tasks(
        self, items: list[tuple[Pet, CareTask]], budget: int
    ) -> tuple[list[tuple[Pet, CareTask, int]], list[dict]]:
        """Split items into (selected, skipped) against the time budget."""
        selected: list[tuple[Pet, CareTask, int]] = []
        skipped: list[dict] = []
        used = 0

        for pet, task in items:
            # Count the buffer here too, so selection cannot approve a set that
            # _assign_times then overruns.
            gap = self.buffer_minutes if selected else 0
            remaining = max(budget - used - gap, 0)

            if task.fits_in(remaining):
                selected.append((pet, task, task.duration_minutes))
                used += gap + task.duration_minutes
                continue

            # Selected items carry the minutes actually booked, which is the
            # full duration unless allow_partial shortened it.
            if self.allow_partial and remaining >= MIN_PARTIAL_MINUTES:
                selected.append((pet, task, remaining))
                used += gap + remaining
                continue

            skipped.append(
                {
                    "pet": pet,
                    "task": task,
                    "reason": f"needs {task.duration_minutes} min, only {remaining} min left",
                }
            )

        return selected, skipped

    def _assign_times(
        self, items: list[tuple[Pet, CareTask, int]], start: time
    ) -> list[dict]:
        """Walk the clock forward from `start`, assigning each task a slot."""
        entries: list[dict] = []
        cursor = datetime.combine(date.min, start)
        total = len(items)

        for position, (pet, task, minutes) in enumerate(items, start=1):
            if position > 1:
                cursor += timedelta(minutes=self.buffer_minutes)
            end = cursor + timedelta(minutes=minutes)

            reason = f"{task.priority} priority, {position} of {total}"
            if minutes < task.duration_minutes:
                reason += f"; shortened from {task.duration_minutes} min to fit"

            entries.append(
                {
                    "pet": pet,
                    "task": task,
                    "title": task.title,
                    "priority": task.priority,
                    "notes": task.notes,
                    "start_time": cursor.time(),
                    "end_time": end.time(),
                    "scheduled_minutes": minutes,
                    "reason": reason,
                }
            )
            cursor = end

        return entries
