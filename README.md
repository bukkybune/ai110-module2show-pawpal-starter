# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## Features

**Scheduling**

- **Cross-pet priority.** Every pet's tasks compete for one time budget on a single
  timeline, so a cat's urgent medication beats a dog's optional grooming regardless of
  which animal was added first.
- **Sorting by time.** Tasks with a fixed window are placed first and in clock order;
  everything else is sorted by priority, then shortest-first so leftover minutes get used.
- **Time windows.** A task can be pinned with `earliest` / `latest` — medication at
  breakfast, a vet call when the vet answers.
- **Buffer-aware budgeting.** The gap between tasks is counted against the day, so a plan
  can never overrun the time available.
- **Partial booking (optional).** A task can be shortened to the minutes that remain
  rather than dropped entirely.
- **Per-pet caps (optional).** Stop one animal consuming the whole day.

**Recurrence**

- **Daily, weekly-by-weekday, and every-N-days** schedules.
- **Per-date completion history**, so finishing today's walk does not cancel tomorrow's.
- **Automatic next occurrence.** Completing a dated recurring task creates the next one.
- **Overdue detection.** A missed occurrence is spotted and moved up the list.
- **Look-ahead.** See what falls due on a future day before it arrives.

**Conflicts and warnings**

- **Clash warnings.** Two tasks wanting the same moment produce a readable warning; the
  scheduler then shifts one rather than failing.
- **Dose spacing.** `min_gap_from` holds a repeat dose a set number of hours after the first.
- **Rest gaps.** `avoid_after` keeps a brisk walk from starting the moment feeding ends.
- **Over-commitment warning** before you read the timetable, not after.
- **Every omission explained.** Nothing is dropped silently; skipped tasks are listed with
  a reason, highest priority first.

**Filtering**

- By pet, by pending/complete status, and by a minimum priority floor.

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
python -m pytest
```

49 tests in `tests/test_pawpal.py`, covering both the happy paths and the edge cases:

| Area | What is verified |
|------|------------------|
| Sorting | Tasks return in chronological order, untimed ones last; planning order respects window, priority, duration and pet |
| Filtering | By pet name, by pending/complete status, and by a minimum priority floor |
| Recurrence | Daily, weekly-by-weekday and interval schedules; completing a dated daily task creates tomorrow's copy; rule-based tasks never duplicate |
| Conflicts | Two tasks at the same time produce a warning and still get scheduled; back-to-back tasks are not flagged; rest gaps and dose spacing are enforced |
| Time budget | Gaps count against the day; over-commitment is warned about; per-pet caps hold; partial booking shortens a task to fit |
| Completion | Status is stored per date, so finishing today does not cancel tomorrow; overdue tasks are detected and moved up |
| Edge cases | A pet with no tasks, an owner with no pets, a zero-minute day, a sliver of time too small to use, an empty sort |
| Guard rails | Duplicate task ids and pet names rejected; missing ids report failure instead of raising; an invalid edit rolls back |

Test run:

```
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/dorcasibrahim/ai110-module2show-pawpal-starter-1
collected 49 items

tests/test_pawpal.py .................................................   [100%]

============================== 49 passed in 0.09s ==============================
```

### Confidence level

**★★★★☆ (4 / 5)**

Four stars rather than five. The scheduling rules themselves are well covered — every
constraint the scheduler enforces has at least one test that fails if the rule is removed,
and the edge cases that usually break schedulers (empty inputs, a zero-minute day, two
tasks wanting one slot) are all pinned down. Two tests exist specifically because a bug was
found while building the demo rather than by writing tests first, which is a good sign that
the suite reflects real failures.

What holds it back from five:

- **Interactions between constraints are under-tested.** Each rule is checked mostly on its
  own. A task that is simultaneously anchored, overdue, and subject to a rest gap takes a
  path no single test covers.
- **The greedy placement is not tested for quality, only legality.** Tests confirm the plan
  is valid; none assert it is the *best* arrangement, because the algorithm does not promise
  one.
- **No property-based or randomised testing.** Everything is a hand-picked scenario, so an
  unusual combination of times and durations could still surprise it.
- **The Streamlit layer has no automated tests.** It was verified by hand with Streamlit's
  `AppTest` harness during development, but that is not part of the suite.

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

There are two ways to run PawPal+: the Streamlit app for interactive use, and
`main.py` for a scripted tour of the logic in the terminal.

### The Streamlit app

```bash
streamlit run app.py
```

**What you can do**

| Area | Actions |
|------|---------|
| Sidebar — *Your day* | Set your name, how many minutes you have, and what time the day starts |
| Sidebar — *Scheduling style* | Set the gap between tasks, allow tasks to be shortened to fit, cap the minutes any one pet can take |
| Sidebar — *Filters* | Limit the plan to chosen pets, or to a minimum priority |
| Pets | Add a pet with name, species and breed. Duplicate names are refused |
| Add a care task | Choose the pet, title, duration, priority and notes; set it to repeat daily, weekly on chosen weekdays, or every N days; optionally pin it to a fixed time window |
| On the list | See every task in the order the day will run, mark one done, or remove it. A repeating task shows ↻, a timed one shows its time, a finished one is struck through |
| Today's schedule | Generate the timetable, see the time breakdown, read why the plan looks the way it does |

**An example workflow**

1. **Add a second pet.** Type `Biscuit`, choose `cat`, press **Add pet**. A green
   confirmation appears and Biscuit joins the pet list.
2. **Give Mochi a routine task.** Task `Morning walk`, 30 minutes, high priority, repeats
   `daily`. Press **Add task**.
3. **Give Biscuit a timed task.** Task `Meds`, 5 minutes, high priority, note
   `with food`, tick **This task has a fixed time window**, set *Not before* 08:00 and
   *Finish by* 09:00.
4. **Create a clash on purpose.** Add `Vet call` for Mochi and `Groomer call` for Biscuit,
   both 30 minutes, both pinned to 09:00. A warning appears immediately, while you are
   still looking at the form:

   > ⚠️ clash: Vet call (Mochi) 09:00-09:30 overlaps Groomer call (Biscuit) 09:00-09:30.
   > One of them will be moved to the next free slot.

5. **Generate the schedule.** The timetable appears with four metrics above it — tasks
   scheduled, minutes on tasks, minutes on gaps, minutes spare. The shifted appointment is
   labelled `moved from 09:00` in its own column, so a rescheduled vet call cannot be
   missed at a glance.
6. **Mark something done.** Press **Done** on the morning walk. It is struck through, and
   because it repeats daily it reappears under **Due tomorrow**.
7. **Read the reasoning.** Open *Why this plan?* for a line-by-line explanation, and
   *Left out* for anything that did not fit and why.

**Key scheduler behaviors on show**

- *Sorting* — the task list and the timetable are both ordered by `Scheduler.sort_by_time()`
  and the planning sort, not by the order you typed things in.
- *Conflict warnings* — raised by `Scheduler.detect_conflicts()` as soon as a clash exists,
  repeated above the timetable, and resolved by shifting rather than failing.
- *Filtering* — the sidebar filters feed straight into `build_household_plan()`.
- *Recurrence* — repeating tasks return the next day via the completion history, and
  **Due tomorrow** previews them with `Scheduler.tasks_due_on()`.
- *Honest accounting* — the metrics separate task time from gap time, so the spare figure
  is real.

### The terminal demo

```bash
python main.py
```

Builds an owner with two pets and eleven tasks **added deliberately out of order**, then
walks through the logic in five sections. Abridged output:

```
======================================================================
1. Sorting — as entered, then sorted by time
======================================================================
As entered:
  Grooming (45 min) [low]
  Vet call (30 min) [high] {from 09:00}
  Nail trim (15 min) [low]
  Morning walk (30 min) [high]
  ...

Sorted by time (untimed tasks last):
  08:00  Meds
  09:00  Vet call
  09:00  Groomer call
    --    Grooming
    --    Nail trim

======================================================================
2. Filtering — by pet, then by status
======================================================================
  Mochi: Grooming, Vet call, Nail trim, Morning walk, Training, Breakfast
  Biscuit: Play session, Groomer call, Litter box, Meds, Meds (evening)

  (marked Training complete)
  complete: Training

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

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

## 📐 System Diagram

The final class design is in [`diagrams/uml_final.mmd`](diagrams/uml_final.mmd), verified
against `pawpal_system.py` so every class, attribute and method on the diagram exists in
the code. [`diagrams/uml.mmd`](diagrams/uml.mmd) is kept alongside it as the diagram the
build was driven from.
