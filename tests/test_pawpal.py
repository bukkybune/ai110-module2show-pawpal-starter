from pawpal_system import Task, Pet, Priority


def test_mark_complete_changes_status():
    task = Task(name="Morning Walk", category="exercise", duration_minutes=30, priority=Priority.HIGH)
    assert task.is_complete is False
    task.mark_complete()
    assert task.is_complete is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Buddy", species="Dog", age=3)
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task(name="Feeding", category="feeding", duration_minutes=10, priority=Priority.HIGH))
    assert len(pet.get_tasks()) == 1
