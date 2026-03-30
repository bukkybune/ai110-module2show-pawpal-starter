from dataclasses import dataclass, field


@dataclass
class Owner:
    name: str
    available_minutes_per_day: int
    preferred_time_of_day: str = "morning"
    notes: str = ""

    def update_info(self, **kwargs):
        pass

    def get_available_time(self):
        pass


@dataclass
class Pet:
    name: str
    species: str
    age: int
    special_needs: str = ""

    def get_profile(self):
        pass

    def update_info(self, **kwargs):
        pass


@dataclass
class Task:
    name: str
    category: str
    duration_minutes: int
    priority: str
    is_recurring: bool = False
    notes: str = ""

    def get_summary(self):
        pass

    def is_schedulable(self, available_minutes):
        pass


class Scheduler:
    def __init__(self, tasks, available_minutes):
        self.tasks = tasks
        self.available_minutes = available_minutes

    def generate_plan(self):
        pass

    def sort_by_priority(self):
        pass

    def filter_by_priority(self):
        pass

    def explain_reasoning(self):
        pass
