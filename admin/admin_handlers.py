import logging
from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
from states.admin import AdminState
from database import Database
import config
from handlers.user_handlers import send_main_menu

logger = logging.getLogger(__name__)

def get_admin_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Розсилка 📢"), types.KeyboardButton(text="Змінити статус команди 🔄")],
            [types.KeyboardButton(text="Змінити стан події ⚙️"), types.KeyboardButton(text="Вихід з адмінпанелі 🚪")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def register_admin_handlers(dp: Dispatcher, db: Database, bot):
    @dp.message(lambda message: message.text and message.text.lower() == config.ADMIN_ENTRY_PHRASE.lower())
    async def process_admin_entry(message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state is None:
            logger.info(f"Received admin entry phrase from user {message.from_user.id}")
            await state.clear()
            await message.answer("Введіть пароль для адмінпанелі:")
            await state.set_state(AdminState.password)

    @dp.message(AdminState.password)
    async def process_admin_password(message: types.Message, state: FSMContext):
        if message.text == config.ADMIN_PASSWORD:
            await message.answer("Вітаю, ви в адмінпанелі!", reply_markup=get_admin_menu_keyboard())
            await state.set_state(AdminState.main)
        else:
            await message.answer("Неправильний пароль. Спробуйте ще раз.")
            await state.set_state(AdminState.password)

    @dp.message(lambda message: message.text in ["Розсилка 📢", "Змінити статус команди 🔄", "Змінити стан події ⚙️", "Вихід з адмінпанелі 🚪"], AdminState.main)
    async def process_admin_menu(message: types.Message, state: FSMContext):
        if message.text == "Розсилка 📢":
            await message.answer("Введіть текст для розсилки:")
            await state.set_state(AdminState.broadcast)
        elif message.text == "Змінити статус команди 🔄":
            await message.answer(
                "Введіть команду у форматі:\n"
                "/set_team_status <team_name> <test_task_status> <is_participant>\n"
                "Наприклад: /set_team_status жопа true true"
            )
            await state.set_state(AdminState.team_status)
        elif message.text == "Змінити стан події ⚙️":
            await message.answer(
                "Введіть команду у форматі:\n"
                "/set_event_state <state>\n"
                "Допустимі стани: registration, test_task, main_task, finished\n"
                "Наприклад: /set_event_state test_task"
            )
            await state.set_state(AdminState.event_state)
        elif message.text == "Вихід з адмінпанелі 🚪":
            await state.clear()
            await send_main_menu(message, state, db, registered=db.is_user_registered(message.from_user.id), name=db.get_user_data(message.from_user.id))

    @dp.message(AdminState.main)
    async def process_invalid_admin_menu(message: types.Message, state: FSMContext):
        await message.answer("Вітаю, ви в адмінпанелі!\n‼️ Будь ласка, вибери один із варіантів нижче!", reply_markup=get_admin_menu_keyboard())

    @dp.message(AdminState.broadcast)
    async def process_broadcast_text(message: types.Message, state: FSMContext):
        broadcast_text = message.text
        try:
            participants = db.get_participants()
            failed_count = 0
            for participant in participants:
                if "chat_id" in participant:
                    try:
                        await bot.send_message(
                            chat_id=participant["chat_id"],
                            text=broadcast_text,
                            parse_mode="Markdown"
                        )
                    except TelegramForbiddenError:
                        logger.warning(f"User {participant['user_id']} blocked the bot, skipping.")
                        failed_count += 1
                    except Exception as e:
                        logger.error(f"Error sending broadcast to user {participant['user_id']}: {e}")
                        failed_count += 1
            await message.answer(f"Розсилка завершена. Успішно надіслано: {len(participants) - failed_count}/{len(participants)}.")
        except Exception as e:
            logger.error(f"Error during broadcast: {e}")
            await message.answer("Виникла помилка під час розсилки.")
        await message.answer("Вітаю, ви в адмінпанелі!", reply_markup=get_admin_menu_keyboard())
        await state.set_state(AdminState.main)

    @dp.message(Command("set_team_status"), AdminState.team_status)
    async def set_team_status(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if user_id not in config.ADMIN_ID:
            logger.warning(f"User {user_id} attempted /set_team_status but is not in ADMIN_ID: {config.ADMIN_ID}")
            await message.answer("Ви не маєте прав для виконання цієї команди! 🚫")
            await message.answer("Вітаю, ви в адмінпанелі!", reply_markup=get_admin_menu_keyboard())
            await state.set_state(AdminState.main)
            return
        args = message.text.split(maxsplit=3)
        if len(args) != 4:
            await message.answer(
                "Використовуйте: /set_team_status <team_name> <test_task_status> <is_participant>\n"
                "Наприклад: /set_team_status жопа true true"
            )
            return
        team_name, test_task_status_str, is_participant_str = args[1], args[2].lower(), args[3].lower()
        if test_task_status_str not in ["true", "false"] or is_participant_str not in ["true", "false"]:
            await message.answer(
                "Значення test_task_status і is_participant повинні бути 'true' або 'false'!\n"
                "Наприклад: /set_team_status жопа true true"
            )
            return
        test_task_status = test_task_status_str == "true"
        is_participant = is_participant_str == "true"
        try:
            result = db.teams.update_one(
                {"team_name": team_name, "category": "CTF2025"},
                {"$set": {"test_task_status": test_task_status, "is_participant": is_participant}}
            )
            if result.matched_count == 0:
                await message.answer(f"Команду {team_name} не знайдено! 😢")
            else:
                await message.answer(
                    f"Статус команди {team_name} оновлено: "
                    f"test_task_status={test_task_status}, is_participant={is_participant} 🚩"
                )
                logger.info(f"Team {team_name} status updated by admin {user_id}")
        except Exception as e:
            logger.error(f"Error updating team {team_name} status: {e}")
            await message.answer("Виникла помилка при оновленні статусу команди! 😓")
        await message.answer("Вітаю, ви в адмінпанелі!", reply_markup=get_admin_menu_keyboard())
        await state.set_state(AdminState.main)

    @dp.message(Command("set_event_state"), AdminState.event_state)
    async def set_event_state(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if user_id not in config.ADMIN_ID:
            logger.warning(f"User {user_id} attempted /set_event_state but is not in ADMIN_ID: {config.ADMIN_ID}")
            await message.answer("Ви не маєте прав для виконання цієї команди! 🚫")
            await message.answer("Вітаю, ви в адмінпанелі!", reply_markup=get_admin_menu_keyboard())
            await state.set_state(AdminState.main)
            return
        args = message.text.split(maxsplit=1)
        if len(args) != 2:
            await message.answer(
                "Використовуйте: /set_event_state <state>\n"
                "Допустимі стани: registration, test_task, main_task, finished\n"
                "Наприклад: /set_event_state test_task"
            )
            return
        new_state = args[1].lower()
        valid_states = ["registration", "test_task", "main_task", "finished"]
        if new_state not in valid_states:
            await message.answer(
                f"Невірний стан! Допустимі стани: {', '.join(valid_states)}\n"
                "Наприклад: /set_event_state test_task"
            )
            return
        try:
            db.event_state.update_one(
                {"event_id": "CTF2025"},
                {"$set": {"current_state": new_state}},
                upsert=True
            )
            await message.answer(f"Стан події оновлено: {new_state} ⚙️")
            logger.info(f"Event state updated to {new_state} by admin {user_id}")
        except Exception as e:
            logger.error(f"Error updating event state: {e}")
            await message.answer("Виникла помилка при оновленні стану події! 😓")
        await message.answer("Вітаю, ви в адмінпанелі!", reply_markup=get_admin_menu_keyboard())
        await state.set_state(AdminState.main)