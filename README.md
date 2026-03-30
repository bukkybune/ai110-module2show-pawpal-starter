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

## Testing PawPal+

### Running the tests

```bash
python -m pytest tests/test_pawpal.py -v
```

### What the tests cover

14 tests across four areas:

| Area | What is verified |
|---|---|
| **Task completion** | `mark_complete()` flips status; adding a task increases the pet's task count |
| **Sorting** | Tasks return in chronological order; unscheduled tasks are placed last; all-unscheduled lists return intact |
| **Recurrence** | Daily tasks produce a next occurrence dated +1 day; weekly tasks +7 days; non-recurring tasks return `None` and add nothing; the original is marked done while the new copy is pending |
| **Conflict detection** | Two pending tasks at the same time produce a warning; unique times produce none; completed tasks sharing a time slot are ignored |
| **Schedule generation** | Tasks too long for remaining time are skipped; already-completed tasks never appear in the plan |

### Confidence level

⭐⭐⭐⭐ (4/5)

The core scheduling logic, recurrence, and conflict detection are all tested against the behaviors most likely to break silently. One star is withheld because the conflict detector only checks exact time-slot matches and does not detect overlapping durations — a known tradeoff documented in `reflection.md`. Edge cases around that gap are untested.

---

## Smarter Scheduling

Beyond basic task generation, the scheduler includes several features for more realistic daily planning:

- **Time-based sorting** — tasks can be assigned a `scheduled_time` in `HH:MM` format and sorted chronologically; tasks without a time slot are placed at the end.
- **Status and pet filtering** — tasks can be filtered by completion status (pending or done) or by which pet they belong to, making it easy to view a specific animal's workload.
- **Recurring task auto-renewal** — marking a recurring task complete via `Scheduler.complete_task()` automatically creates the next occurrence with an updated due date: today + 1 day for daily tasks, today + 7 days for weekly tasks.
- **Conflict detection** — `Scheduler.detect_conflicts()` scans all pending tasks and returns a warning for any two tasks sharing the same start time, helping the owner spot scheduling mistakes before the plan is generated.
