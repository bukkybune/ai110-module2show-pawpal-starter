"""PawPal+ logic layer.

Backend classes for the pet care planning assistant. Mirrors diagrams/uml.mmd.
Keep the two in sync as the design changes.

These are stubs: attributes are defined, method bodies are not implemented yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time


@dataclass
class CareTask:
    """A single unit of pet care work (walk, feeding, meds, grooming...)."""

    task_id: str
    title: str
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"
    recurrence: str | None = None  # "daily" | "weekly" | None
    notes: str | None = None

    def fits_in(self, remaining_minutes: int) -> bool:
        """Return True if this task can be completed within the time left."""
        raise NotImplementedError

    def is_due_today(self, day: date) -> bool:
        """Return True if this task should be scheduled on the given day."""
        raise NotImplementedError

    def summary(self) -> str:
        """One-line display form, e.g. 'Morning walk (30 min) [high]'."""
        raise NotImplementedError


@dataclass
class Pet:
    """A pet and the care tasks that belong to it."""

    name: str
    species: str  # "dog" | "cat" | "other"
    breed: str | None = None
    age_years: int | None = None
    tasks: list[CareTask] = field(default_factory=list)

    def add_task(self, task: CareTask) -> None:
        """Attach a care task to this pet."""
        raise NotImplementedError

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by id. Return True if a task was removed."""
        raise NotImplementedError

    def update_task(self, task_id: str, fields: dict) -> bool:
        """Update fields on a task by id. Return True if a task was updated."""
        raise NotImplementedError

    def list_tasks(self) -> list[CareTask]:
        """Return this pet's tasks."""
        raise NotImplementedError


@dataclass
class Owner:
    """The person doing the care, and the constraints on their day."""

    name: str
    available_minutes: int
    preferred_start_time: time
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Attach a pet to this owner."""
        raise NotImplementedError

    def get_pet(self, name: str) -> Pet | None:
        """Look up one of this owner's pets by name."""
        raise NotImplementedError


@dataclass
class Scheduler:
    """Builds a daily plan from a pet's tasks and an owner's constraints.

    This is the only class with real scheduling behavior. The private helpers
    exist so each decision (ordering, selection, timing) can be tested alone.
    """

    allow_partial: bool = False  # may a task be shortened to fit?
    buffer_minutes: int = 0  # gap between consecutive tasks

    def build_plan(self, owner: Owner, pet: Pet) -> list[dict]:
        """Return an ordered plan: one dict per scheduled task.

        Each entry carries the task, its start and end time, and the reason
        it was placed there.
        """
        raise NotImplementedError

    def explain(self, plan: list[dict]) -> str:
        """Describe why the plan looks the way it does."""
        raise NotImplementedError

    def _sort_tasks(self, tasks: list[CareTask]) -> list[CareTask]:
        """Order tasks by priority, then by duration."""
        raise NotImplementedError

    def _select_tasks(
        self, tasks: list[CareTask], budget: int
    ) -> tuple[list[CareTask], list[tuple[CareTask, str]]]:
        """Split tasks into (selected, skipped) against the time budget.

        Skipped tasks are paired with the reason they were dropped.
        """
        raise NotImplementedError

    def _assign_times(self, tasks: list[CareTask], start: time) -> list[dict]:
        """Walk the clock forward from `start`, assigning each task a slot."""
        raise NotImplementedError
