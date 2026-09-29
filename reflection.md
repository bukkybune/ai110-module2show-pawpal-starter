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

My scheduler works against five constraints:

1. **Total time available.** The owner says how many minutes they have, and the plan can
   never exceed it. The gaps between tasks count against this too, because five minutes
   of walking between jobs is five minutes genuinely gone.
2. **Priority.** High beats medium beats low, across all pets rather than within one.
3. **Time windows.** Some tasks are not free to float — medication has to land with
   breakfast, the vet call happens when the vet answers. These get `earliest`/`latest`
   and claim their slots before anything else is placed.
4. **Spacing rules.** Two doses of the same medication need hours between them
   (`min_gap_from`), and a brisk walk should not start the moment a deep-chested dog
   finishes eating (`avoid_after`).
5. **Recurrence.** A task only competes for time on a day it is actually due.

I decided the order by asking what an owner would be most upset to get wrong. Missing a
medication dose is worse than missing a grooming session, so priority outranks
convenience. But a *timed* task outranks even a high-priority floating one, because a
task with a window either happens in that window or does not happen at all — whereas a
floating task is only ever moved, never lost. That is why anchored tasks are sorted first
and placed before the rest of the day is filled in.

**b. Tradeoffs**

**The scheduler places tasks greedily, and never reconsiders a placement.**

It walks the task list in priority order and gives each task the earliest legal slot it
can find. Once a task is placed, it stays placed. This is a deliberate tradeoff against
an optimal packing algorithm, which would try combinations to find the arrangement that
fits the most valuable set of tasks into the day.

The cost is real and I can point at it in my own output. When the day is tight, a long
high-priority task can consume time that two shorter medium-priority tasks would have
filled more usefully, and the scheduler will never notice. A best-fit or knapsack
approach would do better on exactly that case.

I think the tradeoff is reasonable here for three reasons. First, the greedy rule is one
an owner can hold in their head — "most important first, and shorter things first when
they tie" — so when the plan looks wrong they can see *why* and fix their inputs. An
optimal packer produces better schedules that are harder to argue with. Second, the
failure mode is mild: the worst case is some unused minutes at the end of the day, which
the plan reports honestly rather than hiding. Third, the day is small. With eight or ten
tasks the difference between greedy and optimal is a few minutes, not a missed dose.

A second, narrower tradeoff worth naming: **conflict detection compares the requested
time windows, not the final schedule.** If two tasks both ask for 09:00, I warn about it,
but the scheduler then quietly shifts the loser to the next free slot rather than
refusing to plan. So the warning describes an intent that clashed, not a timetable that
is broken — the printed plan never actually contains two overlapping entries. I chose
that because a warning the owner can ignore is more useful than a scheduler that gives up
on a day it could still mostly deliver.

---

## 3. AI Collaboration

**a. How you used AI**

I used my AI coding assistant across the whole build, but the value was very uneven
depending on what I asked for.

**What worked best**

1. **Asking it to review its own output before I accepted it.** The single most useful
   prompt of the project was asking it to review the class skeleton for missing
   relationships and logic bottlenecks *before* any logic existed. It found three
   contradictions between methods — `is_due_today()` needed a date that `build_plan()`
   never received, `build_plan()` was discarding the skipped-task list that `explain()`
   needed, and buffer time was being ignored during selection but applied during
   placement. All three would have been painful to unpick later.
2. **Having it run the code, not just write it.** Every claim it made was checked by
   actually running `pytest` or `main.py` and showing me the output. That is what caught
   the rest-gap bug described below.
3. **Structural audits.** Asking it to walk the code with `ast` and list every method
   missing a docstring, or every class member absent from the UML, is far more reliable
   than asking "is my documentation complete?" and trusting the answer.
4. **Small, scoped edits over big rewrites.** Asking for one feature at a time kept the
   diffs reviewable. When I asked for four feature areas at once, the result needed two
   rounds of correction.

**What worked less well**

Open-ended requests like "make the scheduler smarter" produced plausible code that did not
match how a pet owner actually thinks about their morning. The narrower the question, the
better the answer.

**b. Judgment and verification**

**The example I keep coming back to: cross-pet priority.**

When I first saw the two-pet schedule, the dog's low-priority grooming had taken the whole
budget and the cat's medium-priority litter box got nothing. I asked why. The assistant
explained that priority only sorted *within* a pet, offered three options, and recommended
the cheapest one: leave the behavior alone and write it up as a tradeoff.

I disagreed. Finishing one animal before starting the other is defensible for a tidy
codebase but wrong for the actual user — nobody grooms one pet while the other's
medication goes undone. I told it to implement cross-pet priority instead. That meant
restructuring the scheduler to work on `(pet, task)` pairs rather than bare tasks, which
was more work than the recommended option, but it is the behavior the app exists to
provide.

**A second case, where the evidence corrected both of us.**

I asked for a rule preventing a walk from being scheduled straight after feeding. The
assistant implemented `avoid_after` as "must not immediately follow", which sounded right.
Running the demo showed the walk had been pushed to **14:15** — past the evening
medication — because that was technically the first slot not immediately after breakfast.
The rule was satisfied and the schedule was nonsense.

The fix was to change what the rule *means*: not "must not follow", but "must rest 30
minutes after". The walk moved to 08:50 and another pet's task filled the gap. This is the
clearest lesson of the project for me — the code did exactly what was asked, and what was
asked was wrong. I only found out because I read the output of a real run instead of
trusting that passing code was correct code.

**How I verified things generally**

- Ran `python -m pytest` after every change; the suite grew to 49 tests.
- Ran `main.py` and actually read the timetable, rather than checking it did not crash.
- Exercised the Streamlit app with Streamlit's `AppTest` harness, so UI wiring was proven
  rather than assumed.
- Checked documentation against code mechanically — the UML is verified member by member
  against `pawpal_system.py`, so it cannot quietly drift.

---

## 4. Testing and Verification

**a. What you tested**

49 tests in `tests/test_pawpal.py`, grouped by the behavior they protect:

- **Sorting** — tasks return in chronological order with untimed ones last; the planning
  sort respects window, priority, duration and pet together.
- **Filtering** — by pet name, by pending/complete status, and by a minimum priority.
- **Recurrence** — daily, weekly-by-weekday and interval schedules; completing a dated
  daily task creates tomorrow's copy; a rule-based task never duplicates itself.
- **Conflicts** — two tasks at the same time warn and still get scheduled; back-to-back
  tasks are not flagged; dose spacing and rest gaps are enforced.
- **Time budget** — gaps count against the day, over-commitment is warned about, per-pet
  caps hold, and partial booking shortens a task to fit.
- **Edge cases** — a pet with no tasks, an owner with no pets, a zero-minute day, a
  sliver of time too small to use, an empty sort.
- **Guard rails** — duplicate ids and pet names rejected, missing-id operations report
  failure instead of raising, an invalid edit rolls back.

The tests that matter most are the ones tied to a specific way an owner could be let
down. `test_completion_is_per_day_so_daily_tasks_come_back` exists because an early
version of the code marked a task complete forever, which would have silently cancelled a
daily medication from the second day onward. `test_buffer_is_counted_against_the_budget`
exists because selection and placement originally disagreed about whether gaps were real
time, so the app would promise a day that could not physically happen.

**b. Confidence**

**Four out of five.** Every rule the scheduler enforces has at least one test that fails
if the rule is removed, and the edge cases that usually break schedulers — empty inputs, a
zero-minute day, two tasks wanting one slot — are all pinned down. Several tests exist
because a real bug was found by reading demo output, which makes me trust them more than
tests written purely from imagination.

What stops me saying five:

- **Constraint interactions are under-tested.** Each rule is checked mostly in isolation.
  A task that is simultaneously time-windowed, overdue, and subject to a rest gap takes a
  path no single test covers.
- **Only legality is tested, not quality.** The tests confirm a plan is valid; none assert
  it is the *best* arrangement, because the greedy algorithm does not promise one.
- **No randomised or property-based testing.** Every scenario is hand-picked, so an
  unusual combination of durations and windows could still surprise it.
- **The Streamlit layer is not in the suite.** It was checked by hand with `AppTest`
  during development, but those checks were not kept.

With more time, in order: a combined-constraint test built from the hardest realistic
morning I can construct; a property-based test asserting the invariants that must always
hold (no overlaps, never exceeding the budget, every task either scheduled or explained);
a test for a task longer than the entire day; behavior across a midnight boundary, which I
suspect is currently wrong since times are compared on a single fixed date; and keeping
the `AppTest` checks as real tests.

---

## 5. Reflection

**a. What went well**

The part I am most satisfied with is that **the scheduler explains itself**. Every plan
carries the reasoning for what was scheduled and a specific reason for everything that was
not — "needs 45 min, only 5 min left", "not due on 2026-09-29", "already done". Nothing
disappears quietly. That turned out to matter more than I expected: almost every bug I
found, I found by reading an explanation that did not make sense, not by a test failing.

I am also glad I separated the data classes from the decision-making. `Owner`, `Pet` and
`CareTask` hold state; `Scheduler` reads them and owns every rule. That made the private
helpers — sorting, selection, placement — testable one at a time, and it meant adding
cross-pet scheduling changed one class rather than four.

**b. What you would improve**

**The plan is still a dictionary.** `build_household_plan()` returns
`{"plan_date", "entries", "skipped", "warnings", "minutes_used"}`, and every consumer
reaches into it by string key. I kept it that way to stay inside the four-class design,
but it is the weakest part of the code: a typo in a key fails at runtime rather than
immediately, and the shape is documented only in a docstring. A `DailyPlan` class would
fix that, and I would do it first in another iteration.

**Placement is greedy and never reconsiders.** It gives each task the earliest legal slot
and moves on. When the day is tight, a long high-priority task can occupy time that two
shorter tasks would have used better. A best-fit pass would produce better days.

**The two recurrence models are more than this app needs.** Supporting both rule-based
recurrence and dated chains satisfied two different requirements, but a reader has to hold
both in their head, and `is_due_today()` branches on which one is in play. If I were
starting again I would pick one — probably rule-based — and say so plainly.

**c. Key takeaway**

**Working code is not evidence of correct design.** The `avoid_after` rule passed its
test, matched its docstring, and produced a schedule that put a dog's walk at 14:15 for no
sane reason. The implementation was perfect; the rule I had asked for was wrong. I only
caught it because I read the actual output of a real run.

The lesson I am taking forward is that the specification is the part worth arguing about,
and the only reliable way to check a specification is to look at what the system produces
for a realistic case — not at whether it runs, and not at whether the tests are green.

**d. AI strategy**

**On organising the work.** I ran most of this project as one long continuous
conversation rather than separate sessions per phase. That had a real benefit — the
assistant remembered why `avoid_after` had been redesigned, so it did not reintroduce the
old semantics later, and it could keep the UML and README in step with the code without
being re-briefed each time. It also had a cost: by the testing phase, the context was full
of design discussion, and it took a deliberate "audit what already exists before writing
anything" step to stop it re-adding tests that were already there. A fresh session for
testing would have forced that audit naturally instead of me having to ask for it. My
rule for next time: keep one session per *artifact* being changed, and start a new one
whenever the job shifts from building to checking, because checking works better without
the bias of having just written the thing.

**On being the lead architect.** The assistant was consistently faster than me at
producing code and consistently worse than me at deciding what the code should do. Its
default is to satisfy the request in front of it; it recommended documenting the cross-pet
problem as a tradeoff rather than fixing it, because that was the smaller change, and it
was only wrong because it did not weigh what an owner would actually care about. Every
decision that shaped this project — cross-pet priority over per-pet convenience, the rest
gap over the adjacency rule, supporting both recurrence models, four stars instead of five
— was a judgement call about the user, not a technical one, and those were mine to make.

What I got better at was the shape of the questions. "Add conflict detection" produces
something. "Review this for missing relationships and bottlenecks before we write any
logic" produces the three design flaws I would otherwise have shipped. Asking it to check
its own work against the running program, rather than accepting its description of what it
built, is the habit I want to keep.
