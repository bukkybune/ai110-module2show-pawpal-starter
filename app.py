from datetime import date, time

import streamlit as st

from pawpal_system import CareTask, Owner, Pet, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Plan a day of pet care around the time you actually have.")

with st.expander("How this works", expanded=False):
    st.markdown(
        """
Tasks from **all** of your pets compete for the same block of time. The scheduler
sorts them by priority (shortest first within a priority), fills the day until the
time runs out, and tells you what it left out and why.

The gap between tasks is counted against your available time, so a plan can never
overrun the day.
"""
    )


# --- Session state -------------------------------------------------------
# Streamlit re-runs this script on every interaction, so the owner is created
# once and kept in the session vault. Everything else hangs off it.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        name="Jordan", available_minutes=120, preferred_start_time=time(8, 0)
    )
    st.session_state.owner.add_pet(Pet(name="Mochi", species="dog", breed="Corgi"))

if "next_task_id" not in st.session_state:
    st.session_state.next_task_id = 1

owner = st.session_state.owner


def new_task_id() -> str:
    """Hand out a unique task id, since CareTask requires one."""
    task_id = f"t{st.session_state.next_task_id}"
    st.session_state.next_task_id += 1
    return task_id


# --- Owner and day constraints -------------------------------------------
with st.sidebar:
    st.header("Your day")
    owner.name = st.text_input("Owner name", value=owner.name)
    owner.available_minutes = st.number_input(
        "Minutes available", min_value=5, max_value=600, value=owner.available_minutes, step=5
    )
    owner.preferred_start_time = st.time_input("Start at", value=owner.preferred_start_time)

    st.header("Scheduling style")
    buffer_minutes = st.slider("Gap between tasks (min)", 0, 30, 5, step=5)
    allow_partial = st.checkbox(
        "Shorten tasks to fit", value=False, help="Book a task for less than its full length."
    )
    cap_per_pet = st.checkbox("Cap time per pet", value=False)
    max_per_pet = (
        st.number_input("Minutes per pet", min_value=5, max_value=300, value=60, step=5)
        if cap_per_pet
        else None
    )

    st.header("Filters")
    only_pets = st.multiselect(
        "Only these pets", [pet.name for pet in owner.pets], default=[]
    )
    priority_floor = st.selectbox("Minimum priority", ["any", "low", "medium", "high"])


# --- Add a pet -----------------------------------------------------------
st.subheader("Pets")

with st.form("add_pet", clear_on_submit=True):
    cols = st.columns([2, 1, 2])
    pet_name = cols[0].text_input("Pet name")
    pet_species = cols[1].selectbox("Species", ["dog", "cat", "other"])
    pet_breed = cols[2].text_input("Breed (optional)")

    if st.form_submit_button("Add pet"):
        if not pet_name.strip():
            st.error("Give the pet a name.")
        else:
            try:
                owner.add_pet(
                    Pet(
                        name=pet_name.strip(),
                        species=pet_species,
                        breed=pet_breed.strip() or None,
                    )
                )
                st.success(f"Added {pet_name.strip()}.")
            except ValueError as error:
                st.error(str(error))

if owner.pets:
    st.write(" · ".join(f"**{pet.name}** ({pet.species})" for pet in owner.pets))
else:
    st.info("No pets yet. Add one above.")


# --- Add a task ----------------------------------------------------------
st.subheader("Care tasks")

if not owner.pets:
    st.caption("Add a pet first, then you can give it tasks.")
else:
    with st.form("add_task", clear_on_submit=True):
        cols = st.columns([2, 2, 1, 1])
        task_pet_name = cols[0].selectbox("For", [pet.name for pet in owner.pets])
        task_title = cols[1].text_input("Task", value="")
        task_duration = cols[2].number_input("Minutes", min_value=1, max_value=240, value=20)
        task_priority = cols[3].selectbox("Priority", ["high", "medium", "low"])
        task_notes = st.text_input("Notes (optional)", placeholder="e.g. with food")

        if st.form_submit_button("Add task"):
            if not task_title.strip():
                st.error("Give the task a title.")
            else:
                pet = owner.get_pet(task_pet_name)
                try:
                    pet.add_task(
                        CareTask(
                            task_id=new_task_id(),
                            title=task_title.strip(),
                            duration_minutes=int(task_duration),
                            priority=task_priority,
                            notes=task_notes.strip() or None,
                        )
                    )
                    st.success(f"Added {task_title.strip()} for {pet.name}.")
                except ValueError as error:
                    st.error(str(error))

    for pet in owner.pets:
        tasks = pet.list_tasks()
        if not tasks:
            continue

        st.markdown(f"**{pet.name}**")
        for task in tasks:
            cols = st.columns([6, 1, 1])
            mark = "~~" if task.is_complete else ""
            cols[0].write(f"{mark}{task.summary()}{mark}")

            if not task.is_complete and cols[1].button("Done", key=f"done_{task.task_id}"):
                task.mark_complete()
                st.rerun()

            if cols[2].button("Remove", key=f"remove_{task.task_id}"):
                pet.remove_task(task.task_id)
                st.rerun()


# --- Build the schedule --------------------------------------------------
st.divider()
st.subheader("Today's schedule")

if st.button("Generate schedule", type="primary"):
    scheduler = Scheduler(
        buffer_minutes=buffer_minutes,
        allow_partial=allow_partial,
        max_minutes_per_pet=max_per_pet,
    )
    plan = scheduler.build_household_plan(
        owner,
        date.today(),
        only_pets=only_pets or None,
        min_priority=None if priority_floor == "any" else priority_floor,
    )

    for warning in plan["warnings"]:
        st.warning(warning)

    if plan["entries"]:
        st.table(
            [
                {
                    "Start": entry["start_time"].strftime("%H:%M"),
                    "End": entry["end_time"].strftime("%H:%M"),
                    "Task": entry["title"],
                    "Pet": entry["pet"].name,
                    "Minutes": entry["scheduled_minutes"],
                    "Priority": entry["priority"],
                    "Notes": entry["notes"] or "",
                }
                for entry in plan["entries"]
            ]
        )
        booked = sum(entry["scheduled_minutes"] for entry in plan["entries"])
        used = plan["minutes_used"]
        st.caption(
            f"{used} of {owner.available_minutes} minutes used "
            f"({booked} on tasks, {used - booked} on gaps)."
        )
    else:
        st.warning("Nothing fits in the time available.")

    if plan["skipped"]:
        with st.expander(f"Left out ({len(plan['skipped'])})", expanded=True):
            for item in plan["skipped"]:
                st.write(f"**{item['task'].title}** ({item['pet'].name}) — {item['reason']}")

    with st.expander("Why this plan?"):
        st.text(scheduler.explain(plan))
