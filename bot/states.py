from aiogram.fsm.state import StatesGroup, State


class ProfileWizard(StatesGroup):
    city = State()
    budget = State()
    allergies = State()
    goals = State()
    confirm = State()
