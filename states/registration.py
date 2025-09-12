from aiogram.fsm.state import StatesGroup, State

class Registration(StatesGroup):
    name = State()
    age = State()
    university = State()
    new_university = State()
    specialty = State()
    course = State()
    source = State()
    custom_source = State() 
    contact = State()  
    check_data = State()
    data_consent = State()