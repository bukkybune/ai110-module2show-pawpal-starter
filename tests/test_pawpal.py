"""Tests for the PawPal+ logic layer.

Run from the project root:

    python -m pytest
"""

from pawpal_system import COMPLETE, PENDING, CareTask, Pet


def test_mark_complete_changes_task_status():
    """Calling mark_complete() should flip the task out of 'pending'."""
    task = CareTask("t1", "Morning walk", 30, "high")
    assert task.status == PENDING
    assert task.is_complete is False

    task.mark_complete()

    assert task.status == COMPLETE
    assert task.is_complete is True


def test_adding_task_increases_pet_task_count():
    """Each task added to a pet should show up in that pet's task list."""
    pet = Pet("Mochi", "dog")
    assert len(pet.list_tasks()) == 0

    pet.add_task(CareTask("t1", "Breakfast", 10, "high"))
    assert len(pet.list_tasks()) == 1

    pet.add_task(CareTask("t2", "Training", 20, "medium"))
    assert len(pet.list_tasks()) == 2
    assert [task.title for task in pet.list_tasks()] == ["Breakfast", "Training"]
