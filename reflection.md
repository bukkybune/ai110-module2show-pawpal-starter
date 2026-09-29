# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial UML has four classes, organized so that three of them mostly hold data and
only one of them makes decisions.

- **`Owner`** — represents the person doing the care and, more importantly, the
  constraints on their day: how many minutes they actually have (`available_minutes`) and
  when the day starts (`preferred_start_time`). It holds the list of pets. Its only
  responsibility is knowing who is doing the work and what limits they are under.

- **`Pet`** — represents the animal (name, species, and optional breed and age) and owns
  the list of care tasks belonging to it. It is mostly a container, but it is the class
  responsible for adding, updating, and removing tasks, so that tasks always stay attached
  to the right animal once there is more than one pet.

- **`CareTask`** — represents one unit of care work: a title, how long it takes, and how
  important it is, plus optional recurrence and notes. I gave it a small amount of
  behavior rather than making it a plain dictionary, mainly `fits_in()`, so a task can
  answer for itself whether it fits in the time remaining.

- **`Scheduler`** — the only class with real logic. It takes an owner's constraints and a
  pet's tasks and produces the ordered plan. I deliberately split its work into three
  private helpers — sorting by priority, selecting tasks against the time budget, and
  assigning start times — so that each scheduling decision can be tested on its own
  instead of only through the finished plan.

The main principle behind the design was separating the data from the decision-making. The
`Scheduler` reads the other three classes but does not belong to them, which means I can
build an owner, a pet, and a set of tasks in a test and check the scheduling behavior in
isolation. In this first version the plan itself is returned as a simple list of
dictionaries rather than its own class, to keep the design to four classes.

**b. Design changes**

Yes. After generating the class skeleton from my UML, I reviewed it before writing any
logic and found three places where the design could not actually do what I had claimed it
would. I made the following changes.

**1. `build_plan()` now takes a `plan_date`.** I had given `CareTask` an
`is_due_today(day)` method for handling recurring tasks, but `build_plan(owner, pet)` had
no date of its own and therefore nothing to pass to it. The recurrence feature was
unreachable — the method could never be called. Adding the date parameter connected the
two.

**2. `build_plan()` now returns the skipped tasks, not just the scheduled ones.**
Originally it returned a flat list of scheduled entries, even though the helper that
chooses tasks was already producing a list of skipped tasks paired with the reason each
was dropped. That information was being discarded, which meant `explain()` could describe
what made the plan but never what got cut. Since explaining the reasoning is a core
requirement, I changed the return value to a dictionary with `plan_date`, `entries`, and
`skipped`, and `explain()` now takes that whole dictionary.

**3. Buffer time is now counted during task selection.** `Scheduler` has a
`buffer_minutes` setting that puts a gap between consecutive tasks, but only the
time-assignment step knew about it — the selection step compared plain task durations
against the available minutes. The two steps disagreed, so selection would approve a set
of tasks that then overran the day once the gaps were added. With a ten-minute buffer and
six tasks that is a full extra hour. Selection now counts the buffers against the budget.

The common thread is that all three were contradictions *between* methods rather than
mistakes inside any one of them, and I only saw them by reading the finished skeleton as a
whole. That was a useful argument for generating the full set of stubs before implementing
anything.

One change I considered but chose not to make: the plan is still a dictionary rather than
its own `DailyPlan` class, to keep the design at four classes. If tracking entries and
skipped tasks in a raw dictionary becomes awkward in the UI, promoting it to a class is
the change I would make next.

**c. Core user actions**

These are the three things a user should be able to do in PawPal+:

1. **Set up who the plan is for.** The user enters their own name and their pet's basic
   details (name, species) so the app knows whose day it is planning. This information is
   what lets the app address the plan to a specific pet rather than producing a generic
   checklist.

2. **Build up a list of care tasks.** The user adds the things their pet needs — a walk,
   feeding, medication, grooming, playtime — and for each one says roughly how long it
   takes and how important it is. They can keep adding tasks, and revise or remove ones
   they got wrong, until the list reflects a realistic day.

3. **Generate a daily plan and see the reasoning behind it.** The user says how much time
   they actually have, asks the app to build a schedule, and gets back an ordered plan
   showing when each task happens. The app also explains its choices — why high-priority
   tasks came first, and which tasks had to be dropped or moved when the available time
   ran out — so the user can judge whether the plan makes sense and adjust their inputs.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
