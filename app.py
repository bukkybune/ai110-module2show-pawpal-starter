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
        pet_choice = st.selectbox("Assign to pet", [p.name for p in owner.pets])
        task_name = st.text_input("Task name", value="Morning walk")
        category = st.selectbox("Category", ["exercise", "feeding", "meds", "grooming", "enrichment", "other"])
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        priority = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"])
        is_recurring = st.checkbox("Recurring daily?", value=True)
        task_notes = st.text_input("Notes (optional)")
        add_task = st.form_submit_button("Add Task")

    if add_task:
        target_pet = next(p for p in owner.pets if p.name == pet_choice)
        target_pet.add_task(Task(
            name=task_name,
            category=category,
            duration_minutes=int(duration),
            priority=Priority[priority],
            is_recurring=is_recurring,
            notes=task_notes,
        ))
        st.success(f"Task '{task_name}' added to {pet_choice}.")

    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.write("All current tasks:")
        st.table([{
            "Pet": next(p.name for p in owner.pets if t in p.get_tasks()),
            "Task": t.name,
            "Category": t.category,
            "Duration (min)": t.duration_minutes,
            "Priority": t.priority.name,
            "Recurring": t.is_recurring,
        } for t in all_tasks])
    else:
        st.info("No tasks yet.")

st.divider()

# ------------------------------------------------------------------ #
# SECTION 4 — Generate Schedule
# ------------------------------------------------------------------ #
st.subheader("Today's Schedule")

if st.button("Generate Schedule"):
    if not owner.get_all_tasks():
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()

        st.success(f"Scheduled {len(plan)} task(s) within {owner.available_minutes_per_day} available minutes.")

        time_used = sum(t.duration_minutes for t in plan)
        for i, task in enumerate(plan, 1):
            st.markdown(f"**{i}.** {task.get_summary()}")

        st.caption(f"Total time: {time_used} min | Remaining: {owner.available_minutes_per_day - time_used} min")
        st.divider()
        st.markdown("**Reasoning:**")
        st.text(scheduler.explain_reasoning())
