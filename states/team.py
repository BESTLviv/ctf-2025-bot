from aiogram.fsm.state import State, StatesGroup

class TeamCreation(StatesGroup):
    team_name = State()
    team_password = State()
    confirm_data = State()

class TeamJoin(StatesGroup):
    team_name = State()
    team_password = State()

class TeamMenu(StatesGroup):
    main = State()
    cv_menu = State()
    upload_cv = State()

class TeamLeaveConfirm(StatesGroup):
    first_confirm = State()
    second_confirm = State()