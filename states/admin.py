from aiogram.fsm.state import State, StatesGroup

from aiogram.fsm.state import State, StatesGroup

class AdminState(StatesGroup):
    password = State()
    main = State()
    broadcast = State()
    team_status = State() 
    event_state = State() 