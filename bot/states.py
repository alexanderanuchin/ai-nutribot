from aiogram.fsm.state import StatesGroup, State


class ProfileWizard(StatesGroup):
    city = State()
    budget = State()
    allergies = State()
    goals = State()
    confirm = State()


class PlanGeneration(StatesGroup):
    choosing_period = State()
    awaiting_job = State()
    awaiting_regen_choice = State()
