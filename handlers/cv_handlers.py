import logging
from aiogram import Dispatcher, types
from aiogram.fsm.context import FSMContext
from states.team import TeamMenu
from database import Database

logger = logging.getLogger(__name__)

def get_cv_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🫶🏻 Завантажити нове CV")],
            [types.KeyboardButton(text="👀 Переглянути моє CV")],
            [types.KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_back_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

async def get_team_info(db: Database, user_id: int):
    try:
        participant = db.participants.find_one({"user_id": user_id})
        if participant and participant.get("team_id"):
            team = db.teams.find_one({"_id": participant["team_id"]})
            if team:
                team_name = team["team_name"]
                members = team["members"]
                member_names = [member["name"] for member_id in members if (member := db.participants.find_one({"user_id": member_id}))]
                member_list = ", ".join(member_names) if member_names else "Тільки ти"
                return f"Твоя команда: {team_name}\nУчасники: {len(members)}/4\nСклад: {member_list}"
        return None
    except Exception as e:
        logger.error(f"Error fetching team info for user {user_id}: {e}")
        return None

def register_cv_handlers(dp: Dispatcher, db, bot):
    from handlers.team_handlers import get_main_menu_keyboard, get_team_menu_keyboard

    @dp.message(lambda message: message.text == "🏆 Моє CV", TeamMenu.main)
    async def process_cv_menu(message: types.Message, state: FSMContext):
        await message.answer(
            "Це потрібно, бо Твоє резюме побачать круті компанії. Тому це можливість отримати якусь цікаву пропозицію, яка змінить твоє життя 😉",
            reply_markup=get_cv_menu_keyboard()
        )
        await state.set_state(TeamMenu.cv_menu)

    @dp.message(lambda message: message.text == "🫶🏻 Завантажити нове CV", TeamMenu.cv_menu)
    async def process_upload_cv(message: types.Message, state: FSMContext):
        await state.update_data(is_cv_saved=False)
        await message.answer(
            "Завантаж своє CV у форматі PDF (максимум 20 МБ). 😄",
            reply_markup=get_back_keyboard()
        )
        await state.set_state(TeamMenu.upload_cv)

    @dp.message(lambda message: message.text == "Назад", TeamMenu.upload_cv)
    async def process_back_from_upload_cv(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        user_data = await state.get_data()
        is_cv_saved = user_data.get("is_cv_saved", False)
        if not is_cv_saved:
            await message.answer("Файл не було збережено.")
        await message.answer(
            "Це потрібно, бо Твоє резюме побачать круті компанії. Тому це можливість отримати якусь цікаву пропозицію, яка змінить твоє життя 😉",
            reply_markup=get_cv_menu_keyboard()
        )
        await state.set_state(TeamMenu.cv_menu)

    @dp.message(TeamMenu.upload_cv)
    async def process_cv_file(message: types.Message, state: FSMContext, bot):
        user_id = message.from_user.id
        if not message.document:
            await state.update_data(is_cv_saved=False)
            await message.answer("‼️ Будь ласка, завантаж файл у форматі PDF!", reply_markup=get_back_keyboard())
            return
        if message.document.mime_type != "application/pdf":
            await state.update_data(is_cv_saved=False)
            await message.answer("‼️ Файл має бути у форматі PDF!", reply_markup=get_back_keyboard())
            return
        if message.document.file_size > 20 * 1024 * 1024:
            await state.update_data(is_cv_saved=False)
            await message.answer("‼️ Файл занадто великий! Максимальний розмір — 20 МБ. Спробуй ще раз!", reply_markup=get_back_keyboard())
            return

        try:
            db.save_cv(user_id, message.document.file_id, message.document.file_name)
            await state.update_data(is_cv_saved=True)
            await message.answer(
                "Очманіти😳! Твоє CV успішно оновлено! Ти або трішки перебільшуєш свої уміння, або десь з десяти років Сіньйор майстер спорту з усіх видів зламів",
                reply_markup=get_cv_menu_keyboard()
            )
            await state.set_state(TeamMenu.cv_menu)
        except Exception as e:
            logger.error(f"Error saving CV for user {user_id}: {e}")
            await state.update_data(is_cv_saved=False)
            await message.answer(
                "‼️ Виникла помилка при завантаженні CV. Спробуй ще раз!",
                reply_markup=get_cv_menu_keyboard()
            )
            await state.set_state(TeamMenu.cv_menu)

    @dp.message(lambda message: message.text == "👀 Переглянути моє CV", TeamMenu.cv_menu)
    async def process_view_cv(message: types.Message, bot):
        user_id = message.from_user.id
        try:
            cv_data = db.get_cv(user_id)
            if cv_data:
                file_name = cv_data.get("file_name", "cv.pdf")
                await message.answer("Там все чотінько, я перевірила. Ось твоє останнє CV! ❤️‍🔥")
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=cv_data["file_id"],
                    caption="Ось твоє CV!",
                    reply_markup=get_cv_menu_keyboard()
                )
            else:
                await message.answer(
                    "Упс, здається, ти ще не завантажував(-ла) CV! 😅 Спробуй завантажити нове.",
                    reply_markup=get_cv_menu_keyboard()
                )
        except Exception as e:
            logger.error(f"Error retrieving CV for user {user_id}: {e}")
            await message.answer(
                "‼️ Виникла помилка при отриманні CV. Спробуй ще раз!",
                reply_markup=get_cv_menu_keyboard()
            )

    @dp.message(lambda message: message.text == "Назад", TeamMenu.cv_menu)
    async def process_back_to_team_menu(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        team_info = await get_team_info(db, user_id)
        if team_info:
            await message.answer(team_info, reply_markup=get_team_menu_keyboard())
            await state.set_state(TeamMenu.main)
        else:
            await message.answer(
                "‼️ Виникла помилка при отриманні інформації про команду. Спробуй ще раз!",
                reply_markup=get_main_menu_keyboard()
            )
            await state.clear()