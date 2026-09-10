# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

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
