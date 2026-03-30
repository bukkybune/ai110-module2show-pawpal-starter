import streamlit as st
from pawpal_system import Owner, Pet, Task, Priority, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# --- Session state: initialise Owner once, persist across reruns ---
if "owner" not in st.session_state:
    st.session_state.owner = None

# ------------------------------------------------------------------ #
# SECTION 1 — Owner setup
# ------------------------------------------------------------------ #
st.subheader("Owner Info")

with st.form("owner_form"):
    owner_name = st.text_input("Your name", value="Dorcas")
    available_minutes = st.number_input("Minutes available today", min_value=10, max_value=480, value=90)
    preferred_time = st.selectbox("Preferred time of day", ["morning", "afternoon", "evening"])
    submitted = st.form_submit_button("Save Owner Info")

if submitted:
    st.session_state.owner = Owner(
        name=owner_name,
        available_minutes_per_day=int(available_minutes),
        preferred_time_of_day=preferred_time,
    )
    st.success(f"Owner '{owner_name}' saved.")

if st.session_state.owner is None:
    st.info("Fill in your owner info above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

st.divider()

# ------------------------------------------------------------------ #
# SECTION 2 — Add a Pet
# ------------------------------------------------------------------ #
st.subheader("Pets")

with st.form("add_pet_form"):
    pet_name = st.text_input("Pet name")
    species = st.selectbox("Species", ["dog", "cat", "bird", "other"])
    age = st.number_input("Age", min_value=0, max_value=30, value=1)
    special_needs = st.text_input("Special needs (optional)")
    add_pet = st.form_submit_button("Add Pet")

if add_pet:
    if pet_name.strip() == "":
        st.warning("Please enter a pet name.")
    elif any(p.name.lower() == pet_name.strip().lower() for p in owner.pets):
        st.warning(f"A pet named '{pet_name}' already exists.")
    else:
        owner.add_pet(Pet(name=pet_name.strip(), species=species, age=int(age), special_needs=special_needs))
        st.success(f"{pet_name} added!")

if owner.pets:
    for pet in owner.pets:
        st.markdown(f"- **{pet.get_profile()}** — {len(pet.get_tasks())} task(s)")
else:
    st.info("No pets yet. Add one above.")

st.divider()

# ------------------------------------------------------------------ #
# SECTION 3 — Add a Task to a Pet
# ------------------------------------------------------------------ #
st.subheader("Tasks")

if not owner.pets:
    st.info("Add a pet before adding tasks.")
else:
    with st.form("add_task_form"):
        pet_choice   = st.selectbox("Assign to pet", [p.name for p in owner.pets])
        task_name    = st.text_input("Task name", value="Morning walk")
        category     = st.selectbox("Category", ["exercise", "feeding", "meds", "grooming", "enrichment", "other"])
        duration     = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority     = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"])
        scheduled_time = st.text_input("Scheduled time (HH:MM, optional)", value="", placeholder="e.g. 08:00")
        is_recurring = st.checkbox("Recurring?", value=True)
        frequency    = st.selectbox("Frequency", ["daily", "weekly"])
        task_notes   = st.text_input("Notes (optional)")
        add_task     = st.form_submit_button("Add Task")

    if add_task:
        target_pet = next(p for p in owner.pets if p.name == pet_choice)
        target_pet.add_task(Task(
            name=task_name,
            category=category,
            duration_minutes=int(duration),
            priority=Priority[priority],
            scheduled_time=scheduled_time.strip(),
            is_recurring=is_recurring,
            frequency=frequency,
            notes=task_notes,
        ))
        st.success(f"Task '{task_name}' added to {pet_choice}.")

    all_tasks = owner.get_all_tasks()

    if all_tasks:
        scheduler = Scheduler(owner)

        # ── Conflict warnings ─────────────────────────────────────────
        conflicts = scheduler.detect_conflicts(all_tasks)
        if conflicts:
            st.error("**Scheduling conflicts detected** — two or more tasks are set for the same time. "
                     "Update a task's scheduled time to resolve before generating your plan.")
            for warning in conflicts:
                # Extract time slot and task names for a friendlier message
                # warning format: "WARNING: conflict at HH:MM — Task A, Task B"
                details = warning.replace("WARNING: conflict at ", "").split(" — ")
                time_slot = details[0]
                task_names = details[1] if len(details) > 1 else ""
                st.warning(f"**{time_slot}** — {task_names} are scheduled at the same time.")

        # ── Task table sorted by scheduled time ───────────────────────
        sorted_tasks = scheduler.sort_by_time(all_tasks)
        pending  = scheduler.filter_by_status(sorted_tasks, completed=False)
        done     = scheduler.filter_by_status(sorted_tasks, completed=True)

        st.markdown(f"**{len(pending)} pending · {len(done)} completed**")

        def pet_name_for(task):
            for p in owner.pets:
                if task in p.get_tasks():
                    return p.name
            return "—"

        if pending:
            st.markdown("**Pending tasks** (sorted by scheduled time)")
            st.table([{
                "Pet":           pet_name_for(t),
                "Task":          t.name,
                "Category":      t.category,
                "Time":          t.scheduled_time or "—",
                "Duration (min)": t.duration_minutes,
                "Priority":      t.priority.name,
                "Recurring":     f"{t.frequency.capitalize()}" if t.is_recurring else "No",
            } for t in pending])

        if done:
            with st.expander(f"Completed tasks ({len(done)})"):
                st.table([{
                    "Pet":      pet_name_for(t),
                    "Task":     t.name,
                    "Due next": t.due_date or "—",
                } for t in done])
    else:
        st.info("No tasks yet.")

st.divider()

# ------------------------------------------------------------------ #
# SECTION 4 — Generate Schedule
# ------------------------------------------------------------------ #
st.subheader("Today's Schedule")

if st.button("Generate Schedule"):
    all_tasks = owner.get_all_tasks()
    if not all_tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = Scheduler(owner)

        # Block on conflicts before generating
        conflicts = scheduler.detect_conflicts(all_tasks)
        if conflicts:
            st.error("Resolve the scheduling conflicts above before generating your plan.")
        else:
            plan = scheduler.generate_plan()
            time_used = sum(t.duration_minutes for t in plan)
            time_left = owner.available_minutes_per_day - time_used

            # Summary metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Tasks scheduled", len(plan))
            col2.metric("Time used (min)", time_used)
            col3.metric("Time remaining (min)", time_left)

            if plan:
                st.success("Here is today's plan, ordered by priority:")
                st.table([{
                    "#":             i,
                    "Task":          t.name,
                    "Pet":           next(p.name for p in owner.pets if t in p.get_tasks()),
                    "Time":          t.scheduled_time or "—",
                    "Duration (min)": t.duration_minutes,
                    "Priority":      t.priority.name,
                } for i, t in enumerate(plan, 1)])

            if scheduler.skipped:
                with st.expander(f"Skipped tasks ({len(scheduler.skipped)})"):
                    st.caption("These tasks didn't fit within your available time today.")
                    for t in scheduler.skipped:
                        st.warning(f"**{t.name}** — {t.duration_minutes} min ({t.priority.name} priority)")
