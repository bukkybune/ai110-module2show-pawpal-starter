"""PawPal+ logic layer.

Backend classes for the pet care planning assistant. Mirrors diagrams/uml.mmd.
Keep the two in sync as the design changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta

# Higher number wins when sorting. Keeping the ordering in one place means the
# scheduler never has to hardcode a string comparison.
PRIORITY_ORDER = {"low": 1, "medium": 2, "high": 3}

VALID_RECURRENCE = {"daily", "weekly", "interval"}

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

PENDING = "pending"
COMPLETE = "complete"

# A partial task shorter than this is not worth scheduling.
MIN_PARTIAL_MINUTES = 5

# How far back is_overdue looks for a missed occurrence.
OVERDUE_LOOKBACK_DAYS = 60

# Fields a caller is allowed to change after a task is created.
EDITABLE_TASK_FIELDS = {
    "title",
    "duration_minutes",
    "priority",
    "recurrence",
    "weekdays",
    "interval_days",
    "notes",
    "start_date",
    "earliest",
    "latest",
    "min_gap_from",
    "min_gap_minutes",
    "avoid_after",
    "avoid_after_minutes",
}


def _at(day_time: time) -> datetime:
    """Put a clock time on a fixed date so times can be added and compared."""
    return datetime.combine(date.min, day_time)


def as_time(value: time | str | None) -> time | None:
    """Accept either a time object or an 'HH:MM' string, return a time."""
    if value is None or isinstance(value, time):
        return value
    try:
        hours, _, minutes = str(value).partition(":")
        return time(int(hours), int(minutes))
    except ValueError:
        raise ValueError(f"expected a time or 'HH:MM' string, got {value!r}") from None


@dataclass
class CareTask:
    """A single unit of pet care work (walk, feeding, meds, grooming...)."""

    task_id: str
    title: str
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"
    recurrence: str | None = None  # "daily" | "weekly" | "interval" | None
    notes: str | None = None
    start_date: date | None = None  # anchor for weekly/interval recurrence

    # Recurrence detail
    weekdays: set[str] | None = None  # for weekly, e.g. {"mon", "thu"}
    interval_days: int | None = None  # for interval, e.g. every 30 days

    # Time window: the task may not start before `earliest` or finish after `latest`.
    # Both accept an 'HH:MM' string as well as a time object.
    earliest: time | str | None = None
    latest: time | str | None = None

    # Set to pin this task to a single day. A recurring task with a due_date is
    # a chain: completing it spawns the next link (see spawn_next_occurrence).
    # Left as None, the task recurs by rule instead and is never duplicated.
    due_date: date | None = None

    # Conflict rules
    min_gap_from: str | None = None  # task_id this must follow at a distance
    min_gap_minutes: int = 0
    avoid_after: set[str] = field(default_factory=set)  # task_ids needing a rest first
    avoid_after_minutes: int = 30  # how long to rest after those tasks

    # Completion history, one entry per day the task was finished
    completed_on: set[date] = field(default_factory=set)

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

        if self.weekdays is not None:
            self.weekdays = {day.strip().lower()[:3] for day in self.weekdays}
            unknown = self.weekdays - set(WEEKDAYS)
            if unknown:
                raise ValueError(f"unknown weekday(s): {sorted(unknown)}")

        if self.recurrence == "interval" and not (self.interval_days or 0) > 0:
            raise ValueError("recurrence 'interval' needs a positive interval_days")

        if self.duration_minutes <= 0:
            raise ValueError(f"duration_minutes must be positive, got {self.duration_minutes}")

        self.earliest = as_time(self.earliest)
        self.latest = as_time(self.latest)
        if self.earliest and self.latest and self.latest <= self.earliest:
            raise ValueError("latest must be after earliest")

        if self.min_gap_minutes < 0:
            raise ValueError("min_gap_minutes cannot be negative")

        if self.avoid_after_minutes < 0:
            raise ValueError("avoid_after_minutes cannot be negative")

    # --- Priority ---------------------------------------------------------

    @property
    def priority_rank(self) -> int:
        """Numeric priority, so tasks can be sorted without string comparisons."""
        return PRIORITY_ORDER[self.priority]

    def effective_rank(self, day: date) -> int:
        """Priority for sorting, bumped one step when the task is overdue."""
        return self.priority_rank + (1 if self.is_overdue(day) else 0)

    # --- Completion -------------------------------------------------------

    def is_complete_on(self, day: date) -> bool:
        """True if this task was finished on the given day."""
        return day in self.completed_on

    @property
    def is_complete(self) -> bool:
        """True if this task was finished today."""
        return self.is_complete_on(date.today())

    @property
    def status(self) -> str:
        """Today's status, 'pending' or 'complete'."""
        return COMPLETE if self.is_complete else PENDING

    def mark_complete(self, day: date | None = None) -> None:
        """Mark this task done for the given day (today by default)."""
        self.completed_on.add(day or date.today())

    def mark_incomplete(self, day: date | None = None) -> None:
        """Undo a completion for the given day (today by default)."""
        self.completed_on.discard(day or date.today())

    # --- Recurrence -------------------------------------------------------

    def is_due_today(self, day: date) -> bool:
        """Return True if this task should be scheduled on the given day."""
        # A pinned task is due on its own day and no other. Its repeats arrive
        # as fresh tasks from spawn_next_occurrence, so the rules below would
        # otherwise schedule the same chore twice.
        if self.due_date is not None:
            return day == self.due_date

        if self.start_date and day < self.start_date:
            return False

        if self.recurrence is None or self.recurrence == "daily":
            return True

        if self.recurrence == "weekly":
            if self.weekdays:
                return WEEKDAYS[day.weekday()] in self.weekdays
            if self.start_date is None:
                return True  # no anchor to count from
            return (day - self.start_date).days % 7 == 0

        # interval
        if self.start_date is None:
            return True
        return (day - self.start_date).days % self.interval_days == 0

    def next_due_date(self, after: date) -> date | None:
        """The next day this task comes round again, or None if it does not."""
        if self.recurrence is None:
            return None
        if self.recurrence == "daily":
            return after + timedelta(days=1)
        if self.recurrence == "weekly":
            if self.weekdays:
                # Walk forward to the next day of the week that is wanted.
                for step in range(1, 8):
                    candidate = after + timedelta(days=step)
                    if WEEKDAYS[candidate.weekday()] in self.weekdays:
                        return candidate
                return None
            return after + timedelta(days=7)
        return after + timedelta(days=self.interval_days)

    def spawn_next_occurrence(self, after: date | None = None) -> CareTask | None:
        """Build the next link in this task's chain, ready to be scheduled."""
        following = self.next_due_date(after or date.today())
        if following is None:
            return None
        return replace(
            self,
            task_id=f"{self.base_id}@{following.isoformat()}",
            due_date=following,
            completed_on=set(),
            avoid_after=set(self.avoid_after),
        )

    @property
    def base_id(self) -> str:
        """The id without the date stamp, so a chain keeps one identity."""
        return self.task_id.split("@", 1)[0]

    def previous_due_date(self, day: date) -> date | None:
        """The last day before `day` this task was due, if there was one."""
        for step in range(1, OVERDUE_LOOKBACK_DAYS + 1):
            earlier = day - timedelta(days=step)
            if self.start_date and earlier < self.start_date:
                return None
            if self.is_due_today(earlier):
                return earlier
        return None

    def is_overdue(self, day: date) -> bool:
        """True if the previous time this task came due, it was not done."""
        # Without a start_date or any history there is nothing to judge against,
        # so a brand new task is never treated as already behind.
        if self.start_date is None and not self.completed_on:
            return False
        previous = self.previous_due_date(day)
        return previous is not None and previous not in self.completed_on

    # --- Scheduling helpers ----------------------------------------------

    @property
    def is_anchored(self) -> bool:
        """True if this task has a time window rather than floating freely."""
        return self.earliest is not None or self.latest is not None

    def fits_in(self, remaining_minutes: int) -> bool:
        """Return True if this task can be completed within the time left."""
        return self.duration_minutes <= remaining_minutes

    def summary(self) -> str:
        """Return a one-line display form, with notes appended when present."""
        line = f"{self.title} ({self.duration_minutes} min) [{self.priority}]"
        if self.earliest and self.latest:
            line += f" {{{self.earliest:%H:%M}-{self.latest:%H:%M}}}"
        elif self.earliest:
            line += f" {{from {self.earliest:%H:%M}}}"
        elif self.latest:
            line += f" {{by {self.latest:%H:%M}}}"
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

    def mark_task_complete(self, task_id: str, day: date | None = None) -> CareTask | None:
        """Finish a task and, if it is a dated chain, queue up its next turn."""
        day = day or date.today()
        task = self._find_task(task_id)
        if task is None:
            return None

        task.mark_complete(day)

        # Only pinned (due_date) tasks spawn a successor. Rule-based recurring
        # tasks come round on their own, so duplicating them would double-book.
        if task.due_date is None or task.recurrence is None:
            return None

        follow_up = task.spawn_next_occurrence(day)
        if follow_up is None or self._find_task(follow_up.task_id) is not None:
            return None

        self.add_task(follow_up)
        return follow_up

    def filter_tasks(
        self, status: str | None = None, day: date | None = None
    ) -> list[CareTask]:
        """This pet's tasks, narrowed to 'pending' or 'complete' on a day."""
        day = day or date.today()
        if status is None:
            return list(self.tasks)
        if status not in (PENDING, COMPLETE):
            raise ValueError(f"status must be {PENDING!r}, {COMPLETE!r} or None")
        want_done = status == COMPLETE
        return [task for task in self.tasks if task.is_complete_on(day) == want_done]

    def list_tasks(self, day: date | None = None, include_complete: bool = True) -> list[CareTask]:
        """Return this pet's tasks, optionally only those still open on `day`."""
        tasks = list(self.tasks)
        if day is not None and not include_complete:
            tasks = [task for task in tasks if not task.is_complete_on(day)]
        return tasks

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
    max_minutes_per_pet: int | None = None  # cap so one pet cannot take the day

    # --- Public API -------------------------------------------------------

    def build_plan(
        self,
        owner: Owner,
        pet: Pet,
        plan_date: date,
        min_priority: str | None = None,
    ) -> dict:
        """Return the plan for one pet on `plan_date`."""
        items = [(pet, task) for task in pet.list_tasks()]
        return self._plan_items(items, owner, plan_date, min_priority)

    def build_household_plan(
        self,
        owner: Owner,
        plan_date: date,
        only_pets: list[str] | None = None,
        min_priority: str | None = None,
    ) -> dict:
        """Return one plan covering every pet the owner has."""
        # All the pets' tasks compete for the same budget on a single timeline,
        # so a high-priority task beats a low-priority one no matter which
        # animal it belongs to. Planning pets one at a time instead would let
        # the first pet's low-priority tasks crowd out the second pet's urgent
        # ones.
        wanted = None if only_pets is None else {name.lower() for name in only_pets}
        items = [
            (pet, task)
            for pet in owner.pets
            if wanted is None or pet.name.lower() in wanted
            for task in pet.list_tasks()
        ]
        return self._plan_items(items, owner, plan_date, min_priority)

    def sort_by_time(self, tasks: list[CareTask]) -> list[CareTask]:
        """Order tasks by the time they are wanted, untimed ones last."""
        # `earliest` is a time object, so it compares correctly on its own; the
        # first half of the key just pushes the untimed tasks to the back.
        return sorted(tasks, key=lambda task: (task.earliest is None, task.earliest or time.min))

    def filter_tasks(
        self,
        owner: Owner,
        pet_name: str | None = None,
        status: str | None = None,
        day: date | None = None,
    ) -> list[tuple[Pet, CareTask]]:
        """Every (pet, task) across the household matching pet name and status."""
        day = day or date.today()
        if status is not None and status not in (PENDING, COMPLETE):
            raise ValueError(f"status must be {PENDING!r}, {COMPLETE!r} or None")

        wanted = pet_name.strip().lower() if pet_name else None
        return [
            (pet, task)
            for pet in owner.pets
            if wanted is None or pet.name.lower() == wanted
            for task in pet.filter_tasks(status, day)
        ]

    def detect_conflicts(self, owner: Owner, day: date | None = None) -> list[str]:
        """Warn about tasks wanting the same slot, rather than failing on them."""
        day = day or date.today()
        candidates = [
            (pet, task)
            for pet, task in self.filter_tasks(owner, status=PENDING, day=day)
            if task.is_due_today(day)
        ]
        return self._conflict_warnings(candidates)

    def _conflict_warnings(self, candidates: list[tuple[Pet, CareTask]]) -> list[str]:
        """Compare every pair of timed tasks and report the ones that overlap."""
        timed = [(pet, task) for pet, task in candidates if task.earliest]
        timed.sort(key=lambda item: item[1].earliest)

        warnings = []
        for index, (pet, task) in enumerate(timed):
            end = _at(task.earliest) + timedelta(minutes=task.duration_minutes)
            for other_pet, other in timed[index + 1 :]:
                other_end = _at(other.earliest) + timedelta(minutes=other.duration_minutes)
                if _at(task.earliest) < other_end and _at(other.earliest) < end:
                    warnings.append(
                        f"clash: {task.title} ({pet.name}) {task.earliest:%H:%M}-{end:%H:%M} "
                        f"overlaps {other.title} ({other_pet.name}) "
                        f"{other.earliest:%H:%M}-{other_end:%H:%M}"
                    )
        return warnings

    def tasks_due_on(self, owner: Owner, day: date) -> list[tuple[Pet, CareTask]]:
        """Look ahead: every (pet, task) that will come due on a given day."""
        return [
            (pet, task)
            for pet in owner.pets
            for task in pet.list_tasks()
            if task.is_due_today(day) and not task.is_complete_on(day)
        ]

    def upcoming(self, plan: dict, now: time) -> list[dict]:
        """The entries in a plan that have not started yet at `now`."""
        return [entry for entry in plan["entries"] if entry["start_time"] >= now]

    def explain(self, plan: dict) -> str:
        """Describe why the plan looks the way it does, including what was cut."""
        entries = plan["entries"]
        skipped = plan["skipped"]
        lines = [f"Plan for {plan['plan_date'].isoformat()}"]

        for warning in plan["warnings"]:
            lines.append(f"! {warning}")

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

    # --- Planning ---------------------------------------------------------

    def _plan_items(
        self,
        items: list[tuple[Pet, CareTask]],
        owner: Owner,
        plan_date: date,
        min_priority: str | None = None,
    ) -> dict:
        """Shared body of build_plan and build_household_plan."""
        candidates, skipped = self._filter_items(items, plan_date, min_priority)
        warnings = self._warnings(candidates, owner)

        ordered = self._sort_tasks(candidates, plan_date)
        placements, unplaced = self._select_tasks(ordered, owner)
        entries = self._assign_times(placements)

        skipped.extend(unplaced)
        # Lead with the highest-priority casualty rather than insertion order.
        skipped.sort(key=lambda item: -item["task"].priority_rank)

        return {
            "plan_date": plan_date,
            "entries": entries,  # scheduled, in clock order
            "skipped": skipped,  # dicts of (pet, task, reason)
            "warnings": warnings,
            "minutes_used": self._minutes_used(entries),
        }

    def _minutes_used(self, entries: list[dict]) -> int:
        """Budget consumed: the task time plus the gaps between tasks."""
        booked = sum(entry["scheduled_minutes"] for entry in entries)
        return booked + self.buffer_minutes * max(len(entries) - 1, 0)

    def _filter_items(
        self,
        items: list[tuple[Pet, CareTask]],
        plan_date: date,
        min_priority: str | None,
    ) -> tuple[list[tuple[Pet, CareTask]], list[dict]]:
        """Drop tasks that are done, not due, or below the priority floor."""
        floor = PRIORITY_ORDER[min_priority.strip().lower()] if min_priority else 0
        candidates, skipped = [], []

        for pet, task in items:
            # A finished task still shows up in the plan as skipped, so the
            # owner can see it was accounted for rather than forgotten.
            if task.is_complete_on(plan_date):
                skipped.append({"pet": pet, "task": task, "reason": "already done"})
            elif not task.is_due_today(plan_date):
                skipped.append(
                    {
                        "pet": pet,
                        "task": task,
                        "reason": f"not due on {plan_date.isoformat()}",
                    }
                )
            elif task.priority_rank < floor:
                skipped.append(
                    {"pet": pet, "task": task, "reason": f"below {min_priority} priority"}
                )
            else:
                candidates.append((pet, task))

        return candidates, skipped

    def _warnings(self, candidates: list[tuple[Pet, CareTask]], owner: Owner) -> list[str]:
        """Flag problems the owner should see before reading the timetable."""
        warnings = []

        wanted = sum(task.duration_minutes for _, task in candidates)
        gaps = self.buffer_minutes * max(len(candidates) - 1, 0)
        if wanted + gaps > owner.available_minutes:
            over = wanted + gaps - owner.available_minutes
            warnings.append(
                f"over-committed by {over} min: {len(candidates)} task(s) need "
                f"{wanted + gaps} min but only {owner.available_minutes} are available"
            )

        overdue = [task.title for _, task in candidates if task.is_overdue(date.today())]
        if overdue:
            warnings.append(f"overdue, moved up the list: {', '.join(overdue)}")

        # Two tasks asking for the same slot is a warning, not a failure: the
        # scheduler still places one of them and moves the other along.
        warnings.extend(self._conflict_warnings(candidates))

        return warnings

    def _sort_tasks(
        self, items: list[tuple[Pet, CareTask]], plan_date: date
    ) -> list[tuple[Pet, CareTask]]:
        """Order (pet, task) pairs by window, then priority, then duration."""
        # Sorting pairs rather than bare tasks is what lets tasks from
        # different pets compete against each other on one timeline. Anchored
        # tasks come first so they can claim their slots before the floating
        # ones fill the day; the pet name is a tie-break so one animal's tasks
        # stay together rather than interleaving arbitrarily.
        return sorted(
            items,
            key=lambda item: (
                not item[1].is_anchored,
                item[1].earliest or time.min,
                -item[1].effective_rank(plan_date),
                item[1].duration_minutes,
                item[0].name,
            ),
        )

    def _select_tasks(
        self, items: list[tuple[Pet, CareTask]], owner: Owner
    ) -> tuple[list[dict], list[dict]]:
        """Place what fits the budget and the time windows, skip the rest."""
        state = {
            "day_start": _at(owner.preferred_start_time),
            "placements": [],
            "used": 0,
            "per_pet": {},
        }
        unplaced: list[dict] = []

        for pet, task in items:
            outcome = self._place_one(pet, task, owner, state)
            if outcome is not None:
                unplaced.append(outcome)

        return state["placements"], unplaced

    def _place_one(self, pet: Pet, task: CareTask, owner: Owner, state: dict) -> dict | None:
        """Put one task on the timeline, or return a record saying why not."""
        placements = state["placements"]
        gap = self.buffer_minutes if placements else 0
        remaining = max(owner.available_minutes - state["used"] - gap, 0)

        minutes = task.duration_minutes
        if not task.fits_in(remaining):
            if not (self.allow_partial and remaining >= MIN_PARTIAL_MINUTES):
                return {
                    "pet": pet,
                    "task": task,
                    "reason": f"needs {task.duration_minutes} min, only {remaining} min left",
                }
            minutes = remaining

        capped = state["per_pet"].get(pet.name, 0) + minutes
        if self.max_minutes_per_pet is not None and capped > self.max_minutes_per_pet:
            return {
                "pet": pet,
                "task": task,
                "reason": f"{pet.name} is capped at {self.max_minutes_per_pet} min/day",
            }

        start, problem = self._find_slot(task, minutes, placements, state["day_start"])
        if start is None:
            return {"pet": pet, "task": task, "reason": problem}

        placements.append(
            {
                "pet": pet,
                "task": task,
                "minutes": minutes,
                "start": start,
                "end": start + timedelta(minutes=minutes),
            }
        )
        placements.sort(key=lambda placement: placement["start"])
        state["used"] += gap + minutes
        state["per_pet"][pet.name] = capped
        return None

    def _find_slot(
        self, task: CareTask, minutes: int, placements: list[dict], day_start: datetime
    ) -> tuple[datetime | None, str]:
        """Find the earliest legal start for a task, or say why there is none."""
        window_start = max(day_start, self._earliest_legal_start(task, placements, day_start))

        window_end = None
        if task.latest:
            window_end = _at(task.latest)
            if window_start + timedelta(minutes=minutes) > window_end:
                return None, (
                    f"cannot fit {minutes} min between "
                    f"{window_start:%H:%M} and {task.latest:%H:%M}"
                )

        # Candidate starts: the top of the window, or just after anything
        # already on the timeline.
        candidates = [window_start]
        for placement in placements:
            candidates.append(placement["end"] + timedelta(minutes=self.buffer_minutes))
        candidates = sorted({start for start in candidates if start >= window_start})

        for start in candidates:
            end = start + timedelta(minutes=minutes)
            if window_end and end > window_end:
                break  # later candidates are worse
            if self._clash(start, end, placements) is None:
                return start, ""

        if window_end:
            return None, f"no free slot before {task.latest:%H:%M}"
        return None, "no free slot in the day"

    def _earliest_legal_start(
        self, task: CareTask, placements: list[dict], day_start: datetime
    ) -> datetime:
        """The soonest this task may begin, given its window and its rest rules."""
        earliest = _at(task.earliest) if task.earliest else day_start

        # A task that must follow another one cannot start until that task has
        # finished and the required gap has passed.
        if task.min_gap_from:
            predecessor = self._placement_of(task.min_gap_from, placements)
            if predecessor is not None:
                earliest = max(
                    earliest, predecessor["end"] + timedelta(minutes=task.min_gap_minutes)
                )

        # Incompatible adjacency: a brisk walk should not start the moment
        # feeding ends, so the task rests for a while after those tasks.
        for placement in placements:
            if placement["task"].task_id in task.avoid_after:
                earliest = max(
                    earliest, placement["end"] + timedelta(minutes=task.avoid_after_minutes)
                )

        return earliest

    @staticmethod
    def _placement_of(task_id: str, placements: list[dict]) -> dict | None:
        """Find where a given task was placed, if it made the plan."""
        for placement in placements:
            if placement["task"].task_id == task_id:
                return placement
        return None

    def _clash(self, start: datetime, end: datetime, placements: list[dict]) -> dict | None:
        """Return the first placement that overlaps this slot, buffer included."""
        gap = timedelta(minutes=self.buffer_minutes)
        for placement in placements:
            if start < placement["end"] + gap and placement["start"] < end + gap:
                return placement
        return None

    def _assign_times(self, placements: list[dict]) -> list[dict]:
        """Turn placed tasks into display entries, in clock order."""
        entries: list[dict] = []
        total = len(placements)

        for position, placement in enumerate(sorted(placements, key=lambda p: p["start"]), 1):
            task = placement["task"]
            minutes = placement["minutes"]

            reason = f"{task.priority} priority, {position} of {total}"
            if task.is_anchored:
                reason += "; time-limited"
            if minutes < task.duration_minutes:
                reason += f"; shortened from {task.duration_minutes} min to fit"

            entries.append(
                {
                    "pet": placement["pet"],
                    "task": task,
                    "title": task.title,
                    "priority": task.priority,
                    "notes": task.notes,
                    "start_time": placement["start"].time(),
                    "end_time": placement["end"].time(),
                    "scheduled_minutes": minutes,
                    "reason": reason,
                }
            )

        return entries
