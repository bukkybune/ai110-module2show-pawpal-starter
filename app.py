from datetime import date, time, timedelta

import streamlit as st

from pawpal_system import CareTask, Owner, Pet, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.title("🐾 PawPal+")
st.caption("Plan a day of pet care around the time you actually have.")

with st.expander("How this works", expanded=False):
    st.markdown(
        """
Tasks from **all** of your pets compete for the same block of time. The scheduler
sorts them by priority (shortest first within a priority), fills the day until the
time runs out, and tells you what it left out and why.

- Tasks with a **time window** claim their slot first, because they cannot be moved.
- The **gap between tasks** counts against your available time, so a plan can never
  overrun the day.
- If two tasks want the same moment, you get a **warning** and one is shifted — the
  timetable itself never double-books you.
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

if "plan" not in st.session_state:
    st.session_state.plan = None

owner = st.session_state.owner
today = date.today()


def new_task_id() -> str:
    """Hand out a unique task id, since CareTask requires one."""
    task_id = f"t{st.session_state.next_task_id}"
    st.session_state.next_task_id += 1
    return task_id


def invalidate_plan() -> None:
    """Drop a generated plan once the tasks behind it have changed."""
    st.session_state.plan = None


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
    only_pets = st.multiselect("Only these pets", [pet.name for pet in owner.pets], default=[])
    priority_floor = st.selectbox("Minimum priority", ["any", "low", "medium", "high"])

scheduler = Scheduler(
    buffer_minutes=buffer_minutes,
    allow_partial=allow_partial,
    max_minutes_per_pet=max_per_pet,
)

left, right = st.columns([1, 1])


# --- Pets and tasks ------------------------------------------------------
with left:
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
                    invalidate_plan()
                    st.success(f"Added {pet_name.strip()}.")
                except ValueError as error:
                    st.error(str(error))

    if owner.pets:
        st.write(" · ".join(f"**{pet.name}** ({pet.species})" for pet in owner.pets))
    else:
        st.info("No pets yet. Add one above.")

    st.subheader("Add a care task")

    if not owner.pets:
        st.caption("Add a pet first, then you can give it tasks.")
    else:
        with st.form("add_task", clear_on_submit=True):
            cols = st.columns([2, 3])
            task_pet_name = cols[0].selectbox("For", [pet.name for pet in owner.pets])
            task_title = cols[1].text_input("Task")

            cols = st.columns([1, 1, 2])
            task_duration = cols[0].number_input("Minutes", min_value=1, max_value=240, value=20)
            task_priority = cols[1].selectbox("Priority", ["high", "medium", "low"])
            task_notes = cols[2].text_input("Notes (optional)", placeholder="e.g. with food")

            cols = st.columns([1, 1, 2])
            repeat = cols[0].selectbox("Repeats", ["one-off", "daily", "weekly", "interval"])
            interval_days = cols[1].number_input(
                "Every N days", min_value=1, max_value=365, value=30
            )
            weekdays = cols[2].multiselect(
                "On these days", ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            )

            fixed_time = st.checkbox("This task has a fixed time window")
            cols = st.columns([1, 1])
            earliest = cols[0].time_input("Not before", value=time(9, 0))
            latest = cols[1].time_input("Finish by", value=time(10, 0))

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
                                recurrence=None if repeat == "one-off" else repeat,
                                weekdays=set(weekdays) if weekdays else None,
                                interval_days=int(interval_days),
                                start_date=today if repeat == "interval" else None,
                                earliest=earliest if fixed_time else None,
                                latest=latest if fixed_time else None,
                            )
                        )
                        invalidate_plan()
                        st.success(f"Added {task_title.strip()} for {pet.name}.")
                    except ValueError as error:
                        st.error(str(error))

    # Warn about clashes as soon as they are created, not only at plan time,
    # so the owner can fix the input while they are still looking at it.
    clashes = scheduler.detect_conflicts(owner, today)
    for clash in clashes:
        st.warning(f"⚠️ {clash}. One of them will be moved to the next free slot.", icon="⚠️")


# --- Current task list ---------------------------------------------------
with right:
    st.subheader("On the list")

    any_tasks = any(pet.list_tasks() for pet in owner.pets)
    if not any_tasks:
        st.info("No tasks yet.")

    for pet in owner.pets:
        tasks = pet.list_tasks()
        if not tasks:
            continue

        done = len(pet.filter_tasks(status="complete", day=today))
        st.markdown(f"**{pet.name}** — {len(tasks)} task(s), {done} done")

        # Show them in the order the day will actually run, not insertion order.
        for task in scheduler.sort_by_time(tasks):
            cols = st.columns([7, 1, 1])
            when = f"`{task.earliest:%H:%M}` " if task.earliest else ""
            mark = "~~" if task.is_complete_on(today) else ""
            repeat = f" ↻ {task.recurrence}" if task.recurrence else ""
            cols[0].write(f"{when}{mark}{task.summary()}{mark}{repeat}")

            if not task.is_complete_on(today):
                if cols[1].button("Done", key=f"done_{task.task_id}"):
                    # Goes through the pet so a dated recurring task can queue
                    # up its next occurrence.
                    follow_up = pet.mark_task_complete(task.task_id, today)
                    if follow_up:
                        st.toast(f"Next {follow_up.title} due {follow_up.due_date}")
                    invalidate_plan()
                    st.rerun()

            if cols[2].button("Remove", key=f"remove_{task.task_id}"):
                pet.remove_task(task.task_id)
                invalidate_plan()
                st.rerun()

    tomorrow = today + timedelta(days=1)
    due_tomorrow = scheduler.tasks_due_on(owner, tomorrow)
    if due_tomorrow:
        with st.expander(f"Due tomorrow ({len(due_tomorrow)})"):
            for pet, task in due_tomorrow:
                st.write(f"{pet.name}: {task.title}")


# --- Build the schedule --------------------------------------------------
st.divider()
st.subheader("Today's schedule")

if st.button("Generate schedule", type="primary", disabled=not owner.pets):
    st.session_state.plan = scheduler.build_household_plan(
        owner,
        today,
        only_pets=only_pets or None,
        min_priority=None if priority_floor == "any" else priority_floor,
    )

plan = st.session_state.plan

if plan is None:
    st.info("Set up your pets and tasks, then generate a schedule.")
else:
    for warning in plan["warnings"]:
        st.warning(warning)

    if plan["entries"]:
        booked = sum(entry["scheduled_minutes"] for entry in plan["entries"])
        used = plan["minutes_used"]

        cols = st.columns(4)
        cols[0].metric("Scheduled", f"{len(plan['entries'])} tasks")
        cols[1].metric("On tasks", f"{booked} min")
        cols[2].metric("On gaps", f"{used - booked} min")
        cols[3].metric("Spare", f"{owner.available_minutes - used} min")

        st.table(
            [
                {
                    "Start": entry["start_time"].strftime("%H:%M"),
                    "End": entry["end_time"].strftime("%H:%M"),
                    "Task": entry["title"],
                    "Pet": entry["pet"].name,
                    "Min": entry["scheduled_minutes"],
                    "Priority": entry["priority"],
                    # Flag anchored tasks that could not get the time they asked
                    # for, so a shifted appointment is obvious at a glance.
                    "Note": (
                        f"moved from {entry['task'].earliest:%H:%M}"
                        if entry["task"].earliest
                        and entry["task"].earliest != entry["start_time"]
                        else entry["notes"] or ""
                    ),
                }
                for entry in plan["entries"]
            ]
        )

        if not plan["skipped"]:
            st.success("Everything on the list fits in the day.")
    else:
        st.error("Nothing fits in the time available.")

    if plan["skipped"]:
        with st.expander(f"Left out ({len(plan['skipped'])})", expanded=True):
            for item in plan["skipped"]:
                st.write(f"**{item['task'].title}** ({item['pet'].name}) — {item['reason']}")

    with st.expander("Why this plan?"):
        st.text(scheduler.explain(plan))
