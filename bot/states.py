from aiogram.fsm.state import StatesGroup, State

class ProfileWizard(StatesGroup):
    sex = State()
    birth_date = State()
    height = State()
    weight = State()
    activity = State()
    goal = State()
    allergies = State()
    exclusions = State()
    budget = State()
