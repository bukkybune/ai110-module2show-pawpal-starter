# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Running the logic layer from the terminal:

```bash
python main.py
```

One owner (Jordan, 180 minutes from 08:00) with two pets and eleven care tasks, added to
the system deliberately out of order. The demo walks through sorting, filtering, conflict
detection, the schedule itself, and recurrence.

**Sorting and filtering**

```
======================================================================
1. Sorting — as entered, then sorted by time
======================================================================
As entered:
  Grooming (45 min) [low]
  Vet call (30 min) [high] {from 09:00}
  Nail trim (15 min) [low]
  Morning walk (30 min) [high]
  Training (20 min) [medium]
  Breakfast (10 min) [high]
  ...

Sorted by time (untimed tasks last):
  08:00  Meds
  09:00  Vet call
  09:00  Groomer call
    --    Grooming
    --    Nail trim
    --    Morning walk

======================================================================
2. Filtering — by pet, then by status
======================================================================
  Mochi: Grooming, Vet call, Nail trim, Morning walk, Training, Breakfast
  Biscuit: Play session, Groomer call, Litter box, Meds, Meds (evening)

  (marked Training complete)
  pending: Grooming, Vet call, Nail trim, Morning walk, Breakfast, ...
  complete: Training
```

**Conflicts, the schedule, and recurrence**

```
======================================================================
3. Conflict detection
======================================================================
  ! clash: Vet call (Mochi) 09:00-09:30 overlaps Groomer call (Biscuit) 09:00-09:20

======================================================================
4. TODAY'S SCHEDULE — Tuesday, 29 September 2026
======================================================================
Jordan has 180 minutes from 08:00, across 2 pets (Mochi, Biscuit).

  ! over-committed by 45 min: 9 task(s) need 225 min but only 180 are available
  ! clash: Vet call (Mochi) 09:00-09:30 overlaps Groomer call (Biscuit) 09:00-09:20
----------------------------------------------------------------------
  08:00 - 08:05  Meds           Biscuit    5 min  [high]
                 note: with food
  08:10 - 08:20  Breakfast      Mochi     10 min  [high]
  08:25 - 08:40  Litter box     Biscuit   15 min  [medium]
  09:00 - 09:20  Groomer call   Biscuit   20 min  [high]
  09:25 - 09:55  Vet call       Mochi     30 min  [high]
  10:00 - 10:30  Morning walk   Mochi     30 min  [high]
  10:35 - 11:00  Play session   Biscuit   25 min  [low]
  14:05 - 14:10  Meds (evening) Biscuit    5 min  [high]

  Not today:
    Training (Mochi) — already done
    Nail trim (Mochi) — not due on 2026-09-29
    Grooming (Mochi) — needs 45 min, only 0 min left

----------------------------------------------------------------------
  175 of 180 minutes used (140 on tasks, 35 on gaps), 5 to spare.

======================================================================
5. Recurrence — completing a daily task rolls it forward
======================================================================
  completed Breakfast for 2026-09-29
  created   Breakfast due 2026-09-30 (id m2@2026-09-30)
  task count 6 -> 7
```

Things to notice in the output:

- **Priority beats pet order.** Biscuit's medium-priority litter box is scheduled ahead of
  Mochi's low-priority grooming, even though Mochi was added to the household first.
- **Time windows are respected.** The morning meds must land between 08:00 and 09:00 and
  they take the first slot of the day.
- **A clash warns, it does not crash.** The vet and the groomer both want 09:00. The
  scheduler says so, then places one at 09:00 and shifts the other to 09:25 — so the
  printed timetable never actually contains an overlap.
- **Rest gaps are enforced, not wasted.** The walk waits out a rest period after breakfast
  (a brisk walk on a full stomach risks bloat), and other tasks fill the gap.
- **Doses stay spaced apart.** The evening meds are held until 14:05, six hours after the
  morning dose.
- **Recurring tasks only appear when due.** The nail trim is a Saturday task, so it sits
  out a Tuesday, and completing the daily breakfast creates tomorrow's copy automatically.
- **Nothing disappears silently.** Tasks that do not fit are listed with the reason they
  were left out, highest priority first.

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

All of the scheduling logic lives in `pawpal_system.py`. Public methods are listed first;
the `_private` ones are the individual decisions, split out so each can be tested alone.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `Scheduler._sort_tasks()` | By clock time; by window, priority, duration and pet for planning |
| Filtering | `Scheduler.filter_tasks()`, `Pet.filter_tasks()`, `Scheduler._filter_items()` | By pet, completion status, priority floor and due date |
| Conflict handling | `Scheduler.detect_conflicts()`, `_conflict_warnings()`, `_clash()`, `_earliest_legal_start()` | Warns on overlapping requests, then shifts rather than failing |
| Recurring tasks | `CareTask.is_due_today()`, `next_due_date()`, `spawn_next_occurrence()`, `Pet.mark_task_complete()` | Daily, weekly by weekday, and every-N-days intervals |
| Completion history | `CareTask.mark_complete()`, `is_complete_on()`, `is_overdue()` | Stored per date, so a daily task returns tomorrow |
| Time budget | `Scheduler._select_tasks()`, `_place_one()`, `_minutes_used()` | Gaps between tasks count against the day |

### Sorting

`Scheduler.sort_by_time(tasks)` orders tasks by the time they are wanted, putting untimed
tasks last. Times are stored as `datetime.time` objects, so they compare correctly without
any parsing — the `sorted()` key lambda only exists to push the untimed tasks to the back.
Times may be supplied as `"HH:MM"` strings and are converted on construction by `as_time()`.

Planning uses a wider sort, `_sort_tasks()`, which orders by four things at once: tasks
with a time window first (they cannot be moved, so they claim their slots before the day
fills up), then priority highest-first, then shortest duration, then pet name so one
animal's tasks stay together.

### Filtering

`Scheduler.filter_tasks(owner, pet_name=, status=, day=)` narrows the household's tasks by
animal and by whether they are `"pending"` or `"complete"` on a given day.
`Pet.filter_tasks(status=, day=)` does the same for a single pet.

During planning, `_filter_items()` drops anything already done, not due today, or below an
optional `min_priority` floor — each with a reason recorded, so a filtered task appears in
the plan's skipped list rather than vanishing.

### Conflict detection

`Scheduler.detect_conflicts(owner, day)` compares every pair of timed tasks and returns a
list of plain warning strings. It never raises:

```
! clash: Vet call (Mochi) 09:00-09:30 overlaps Groomer call (Biscuit) 09:00-09:20
```

These warnings also appear in `plan["warnings"]`. The scheduler then places one task at the
requested time and shifts the other to the next free slot, so the printed timetable never
contains an overlap. Three further rules prevent bad placements rather than reporting them:
`_clash()` keeps slots from overlapping, `min_gap_from` holds a repeat dose hours after the
first, and `avoid_after` enforces a rest period (a brisk walk should not start the moment a
deep-chested dog finishes eating).

### Recurring tasks

Two models are supported, and they do not double-book each other.

**Rule-based** (no `due_date`): one task object recurs by calculation.
`CareTask.is_due_today(day)` answers for daily, weekly-by-weekday (`weekdays={"sat"}`) and
interval (`interval_days=30`) schedules. Completions are stored per date in `completed_on`,
so finishing today's walk does not cancel tomorrow's.

**Chained** (with a `due_date`): the task is pinned to one day.
`Pet.mark_task_complete(task_id, day)` marks it done and calls `spawn_next_occurrence()`,
which uses `next_due_date()` and `timedelta` to build the next link:

```
completed Breakfast for 2026-09-29
created   Breakfast due 2026-09-30 (id m2@2026-09-30)
```

`is_due_today()` branches on `due_date`, so a pinned task fires only on its own day and a
rule-based one is never duplicated.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
