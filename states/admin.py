from aiogram.fsm.state import State, StatesGroup

class AdminState(StatesGroup):
    password = State()
    main = State()
    broadcast = State()