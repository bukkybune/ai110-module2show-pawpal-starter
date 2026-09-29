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

One owner (Jordan, 120 minutes from 08:00) with two pets and seven care tasks. All of the
tasks compete for the same time budget on a single timeline, so priority decides what gets
scheduled regardless of which pet a task belongs to:

```
======================================================================
TODAY'S SCHEDULE — Tuesday, 29 September 2026
======================================================================
Jordan has 120 minutes from 08:00, across 2 pets (Mochi, Biscuit).

----------------------------------------------------------------------
  08:00 - 08:05  Meds           Biscuit    5 min  [high]
                 note: with food
  08:10 - 08:20  Breakfast      Mochi     10 min  [high]
  08:25 - 08:55  Morning walk   Mochi     30 min  [high]
  09:00 - 09:15  Litter box     Biscuit   15 min  [medium]
  09:20 - 09:40  Training       Mochi     20 min  [medium]

  Not today:
    Play session (Biscuit) — needs 25 min, only 15 min left
    Grooming (Mochi) — needs 45 min, only 15 min left

======================================================================
80 of 120 minutes planned, 40 to spare.
======================================================================
```

Things to notice in the output:

- **Priority beats pet order.** Biscuit's medium-priority litter box is scheduled ahead of
  Mochi's low-priority grooming, even though Mochi was added to the household first.
- **Buffers are real time.** The five-minute gaps between tasks are counted against the
  budget during selection, so the plan cannot overrun the day.
- **Nothing disappears silently.** Tasks that do not fit are listed with the reason they
  were left out.

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

> Fill in once you've implemented scheduling logic.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | | e.g., by priority, duration |
| Filtering | | e.g., skip tasks if time runs out |
| Conflict handling | | e.g., overlapping time slots |
| Recurring tasks | | e.g., daily vs. weekly |

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
