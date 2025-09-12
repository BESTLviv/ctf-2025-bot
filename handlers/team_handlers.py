import logging
import os
from aiogram import Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from states.team import TeamCreation, TeamJoin, TeamMenu, TeamLeaveConfirm
from database import Database
from handlers.cv_handlers import register_cv_handlers, get_back_keyboard
import config

logger = logging.getLogger(__name__)

def get_main_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Інформація про CTF 🚩"), types.KeyboardButton(text="Хто такі BEST Lviv❓")],
            [types.KeyboardButton(text="Моя команда 🫱🏻‍🫲🏿")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_main_menu_message():
    return (
        "Повертаємось до головного меню! 😊\n"
        "Тепер ти можеш:\n"
        " ✅ Увійти в команду чи створити свою\n"
        " ✅ Дізнатись усе про подію ℹ️\n"
        f"\nЯкщо не маєш команди, з якою хочеш брати участь — пірнай у чат учасників [{config.PARTICIPANTS_CHAT_LINK}]. Там можна легко знайти однодумців! 🤝\n\n"
        "Йо-хо-хо! І флаг у кишеню! Лет’s гоу! 🚩"
    )

def get_team_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🧪 Тестове завдання")],
            [types.KeyboardButton(text="🏆 Моє CV")],
            [types.KeyboardButton(text="🚪 Покинути команду")],
            [types.KeyboardButton(text="Повернутися до головного меню")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_leave_confirm_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Так, впевнений(-а) ✅")],
            [types.KeyboardButton(text="Ні, залишитись ❌")]
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
                return f"Твоя команда: {team_name}\nУчасники: {len(members)}/4\nСклад: {member_list}", team
        return None, None
    except Exception as e:
        logger.error(f"Error fetching team info for user {user_id}: {e}")
        return None, None

async def send_main_menu(message: types.Message, state: FSMContext, error_message: str = None):
    if error_message:
        await message.answer(error_message, reply_markup=get_main_menu_keyboard())
    else:
        await message.answer(get_main_menu_message(), reply_markup=get_main_menu_keyboard())
    await state.clear()

def get_team_creation_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Повернутися до головного меню")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_confirm_data_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Правильно ✅")],
            [types.KeyboardButton(text="Неправильно ❌")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def register_team_handlers(dp: Dispatcher, db: Database, bot):
    register_cv_handlers(dp, db, bot)

    @dp.message(lambda message: message.text == "Моя команда 🫱🏻‍🫲🏿" and db.is_user_registered(message.from_user.id))
    async def process_team(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        team_info, _ = await get_team_info(db, user_id)
        if team_info:
            await message.answer(team_info, reply_markup=get_team_menu_keyboard())
            await state.set_state(TeamMenu.main)
        else:
            image_path = os.path.join(config.ASSETS_PATH, "findTeam.png")
            if not os.path.exists(image_path):
                logger.error(f"Image file not found at {image_path}")
                await message.answer("‼️ Виникла помилка: зображення findTeam.png не знайдено. Але не хвилюйся, продовжимо!")
            else:
                try:
                    photo = FSInputFile(path=image_path)
                    await message.answer_photo(photo=photo, caption="🤝 Знайди свою команду для BEST CTF-2025!")
                except Exception as e:
                    logger.error(f"Failed to send findTeam.png: {str(e)}")
                    await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")

            keyboard = types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="👉 Чат учасників 💭")],
                    [types.KeyboardButton(text="Створити команду 🫱🏻‍🫲🏿")],
                    [types.KeyboardButton(text="Приєднатись до команди 👥")],
                    [types.KeyboardButton(text="Повернутися до головного меню")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await message.answer(
                "❌ Ти поки не в команді.\n\n"
                "Але це не страшно, адже у нас є чат для учасників, які так само шукають собі мейтів, "
                "все що тобі потрібно це перейти в чат і представитись! Хто знає, може саме з цими людьми "
                "ви зійдете на п’єдестал! 🤝\n\n"
                "Або ж створи свою команду і запроси інших героїв просто зараз:",
                reply_markup=keyboard
            )
            await state.clear()

    @dp.message(lambda message: message.text == "👉 Чат учасників 💭")
    async def process_chat_link(message: types.Message):
        image_path = os.path.join(config.ASSETS_PATH, "chat.png")
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at {image_path}")
            await message.answer("‼️ Виникла помилка: зображення chat.png не знайдено. Але не хвилюйся, продовжимо!")
        else:
            try:
                photo = FSInputFile(path=image_path)
                await message.answer_photo(photo=photo, caption="💭 Приєднуйся до чату учасників!")
            except Exception as e:
                logger.error(f"Failed to send chat.png: {str(e)}")
                await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")
        
        await message.answer(
            f"Переходь у чат учасників! 🤝\n{config.PARTICIPANTS_CHAT_LINK}",
            reply_markup=get_main_menu_keyboard()
        )

    @dp.message(lambda message: message.text == "Створити команду 🫱🏻‍🫲🏿")
    async def process_create_team(message: types.Message, state: FSMContext):
        if db.is_user_in_team(message.from_user.id):
            await message.answer(
                "Ти вже в команді! Спочатку покинь поточну команду, щоб створити нову.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        await message.answer("Круто! Давай у кілька натисків по клавіатурі створимо місце, де збираються сильні💪\n\nВведи назву команди:", reply_markup=get_team_creation_keyboard())
        await state.set_state(TeamCreation.team_name)

    @dp.message(TeamCreation.team_name)
    async def process_team_name(message: types.Message, state: FSMContext):
        if message.text == "Повернутися до головного меню":
            await send_main_menu(message, state)
            return
        team_name = message.text.strip()
        if len(team_name) < 2:
            await message.answer("♦️ Введи назву команди:\n‼️ Назва команди має містити принаймні 2 символи. Спробуй ще раз!", reply_markup=get_team_creation_keyboard())
            return
        if db.teams.find_one({"team_name": team_name}):
            await message.answer("♦️ Введи назву команди:\n‼️ Ця назва команди вже зайнята. Вибери іншу!", reply_markup=get_team_creation_keyboard())
            return
        await state.update_data(team_name=team_name)
        await message.answer("Вигадай пароль для команди. Знаю, це складно, але воно точно того варте! 🔒", reply_markup=get_team_creation_keyboard())
        await state.set_state(TeamCreation.team_password)

    @dp.message(TeamCreation.team_password)
    async def process_team_password(message: types.Message, state: FSMContext):
        if message.text == "Повернутися до головного меню":
            await send_main_menu(message, state)
            return
        password = message.text.strip()
        if len(password) < 4:
            await message.answer("♦️ Вигадай пароль для команди. Знаю, це складно, але воно точно того варте! 🔒\n‼️ Пароль має містити принаймні 4 символи. Спробуй ще раз!", reply_markup=get_team_creation_keyboard())
            return
        await state.update_data(team_password=password)
        user_data = await state.get_data()
        await message.answer(
            f"Перевір, чи правильно введено дані:\nНазва команди: {user_data['team_name']}\nПароль: {password}",
            reply_markup=get_confirm_data_keyboard()
        )
        await state.set_state(TeamCreation.confirm_data)

    @dp.message(lambda message: message.text in ["Правильно ✅", "Неправильно ❌"], TeamCreation.confirm_data)
    async def process_confirm_data(message: types.Message, state: FSMContext):
        if message.text == "Правильно ✅":
            user_id = message.from_user.id
            user_data = await state.get_data()
            team_name = user_data["team_name"]
            password = user_data["team_password"]
            try:
                team_id, success = db.add_team(team_name, user_id, password)
                if success:
                    db.participants.update_one({"user_id": user_id}, {"$set": {"team_id": team_id}})
                    team_info, team = await get_team_info(db, user_id)
                    await message.answer(
                        f"Вітаю! Ти створив(-ла) команду *{team_name}*!\n{team_info.split('\n', 1)[1] if team_info and '\n' in team_info else 'Ти єдиний учасник наразі!'}",
                        parse_mode="Markdown",
                        reply_markup=get_team_menu_keyboard()
                    )
                    await state.set_state(TeamMenu.main)
                else:
                    await send_main_menu(message, state, "Цей пароль уже зайнятий, давай інший 😜")
            except Exception as e:
                logger.error(f"Error creating team for user {user_id}: {e}")
                await send_main_menu(message, state, "‼️ Виникла помилка при створенні команди. Спробуй ще раз!")
        else:
            await message.answer("Добре, давай ще раз! Введи назву команди:", reply_markup=get_team_creation_keyboard())
            await state.set_state(TeamCreation.team_name)

    @dp.message(TeamCreation.confirm_data)
    async def process_invalid_confirm_data(message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        await message.answer(
            f"Перевір, чи правильно введено дані:\nНазва команди: {user_data['team_name']}\nПароль: {user_data['team_password']}\n‼️ Будь ласка, вибери один із варіантів нижче!",
            reply_markup=get_confirm_data_keyboard()
        )

    @dp.message(lambda message: message.text == "Приєднатись до команди 👥")
    async def process_join_team(message: types.Message, state: FSMContext):
        if db.is_user_in_team(message.from_user.id):
            await message.answer(
                "Ти вже в команді! Спочатку покинь поточну команду, щоб приєднатися до іншої.",
                reply_markup=get_main_menu_keyboard()
            )
            return
        await message.answer(
            "Зібрався з силами? Приєднуйся до своєї команди! 💪\n\nВведи назву команди:",
            reply_markup=get_team_creation_keyboard()
        )
        await state.set_state(TeamJoin.team_name)

    @dp.message(TeamJoin.team_name)
    async def process_join_team_name(message: types.Message, state: FSMContext):
        if message.text == "Повернутися до головного меню":
            await send_main_menu(message, state)
            return
        team_name = message.text.strip()
        if not db.teams.find_one({"team_name": team_name}):
            await message.answer("♦️ Введи назву команди:\n‼️ Команда з такою назвою не існує. Перевір назву та спробуй ще раз!", reply_markup=get_team_creation_keyboard())
            return
        await state.update_data(team_name=team_name)
        await message.answer(
            "Введи пароль команди. Ти ж його знаєш, правда? 😅",
            reply_markup=get_team_creation_keyboard()
        )
        await state.set_state(TeamJoin.team_password)

    @dp.message(TeamJoin.team_password)
    async def process_join_team_password(message: types.Message, state: FSMContext):
        password = message.text.strip()
        user_id = message.from_user.id
        user_data = await state.get_data()
        team_name = user_data["team_name"]
        try:
            team_id, success = db.add_team(team_name, user_id, password)
            if success:
                db.participants.update_one({"user_id": user_id}, {"$set": {"team_id": team_id}})
                team_info, team = await get_team_info(db, user_id)
                new_member = db.participants.find_one({"user_id": user_id})
                new_member_name = new_member["name"] if new_member else "Новий учасник"
                await message.answer(
                    f"Вітаю, тепер ти успішно доєднався(-лась) до команди *{team_name}*!\n{team_info.split('\n', 1)[1] if team_info and '\n' in team_info else 'Ти приєднався до команди!'}",
                    parse_mode="Markdown",
                    reply_markup=get_team_menu_keyboard()
                )
                await state.set_state(TeamMenu.main)
                for member_id, member in [(m_id, db.participants.find_one({"user_id": m_id})) for m_id in team["members"] if m_id != user_id]:
                    if member and "chat_id" in member:
                        try:
                            await bot.send_message(
                                chat_id=member["chat_id"],
                                text=f"Вітаю, до вашої команди *{team_name}* доєднався(-лась) *{new_member_name}*! Якщо ви не знаєте, хто це, зверніться до {config.ORGANIZER_CONTACT}.",
                                parse_mode="Markdown"
                            )
                        except Exception as e:
                            logger.error(f"Error sending notification to user {member_id}: {e}")
                    else:
                        logger.warning(f"No chat_id found for user {member_id} in team {team_name}")
            else:
                await message.answer(
                    "♦️ Введи пароль команди. Ти ж його знаєш, правда? 😅\n‼️ Неправильний пароль або команда вже повна (4 учасники). Перевір дані та спробуй ще раз!",
                    reply_markup=get_team_creation_keyboard()
                )
        except Exception as e:
            logger.error(f"Error joining team for user {user_id}: {e}")
            await message.answer(
                "♦️ Введи пароль команди. Ти ж його знаєш, правда? 😅\n‼️ Виникла помилка при приєднанні до команди. Спробуй ще раз!",
                reply_markup=get_team_creation_keyboard()
            )

    @dp.message(lambda message: message.text == "Повернутися до головного меню")
    async def process_back_to_main_menu(message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state in [TeamCreation.team_name, TeamCreation.team_password, TeamJoin.team_name, TeamJoin.team_password, TeamLeaveConfirm.first_confirm, TeamLeaveConfirm.second_confirm]:
            await send_main_menu(message, state)
        else:
            await send_main_menu(message, state) 

    @dp.message(lambda message: message.text == "🧪 Тестове завдання", TeamMenu.main)
    async def process_test_task(message: types.Message):
        image_path = os.path.join(config.ASSETS_PATH, "test.png")
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at {image_path}")
            await message.answer("‼️ Виникла помилка: зображення test.png не знайдено. Але не хвилюйся, продовжимо!")
        else:
            try:
                photo = FSInputFile(path=image_path)
                await message.answer_photo(photo=photo, caption="🧪 Готуйся до тестового завдання!")
            except Exception as e:
                logger.error(f"Failed to send test.png: {str(e)}")
                await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")
        
        await message.answer(
            "Йой, його поки тут немає😢 Воно буде 15-го листопада. Заряджай ноут, завантажуй усі словники і будь готовий(-а) до бою🔥\n"
            "‼️ Увага ‼️: брати участь можуть лише команди, у яких є щонайменше 3 учасники.",
            reply_markup=get_back_keyboard()
        )

    @dp.message(lambda message: message.text == "🚪 Покинути команду", TeamMenu.main)
    async def process_leave_team(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        try:
            participant = db.participants.find_one({"user_id": user_id})
            if participant and participant.get("team_id"):
                team = db.teams.find_one({"_id": participant["team_id"]})
                team_name = team["team_name"] if team else "невідома команда"
                await message.answer(
                    f"Ти впевнений(-а), що хочеш покинути команду *{team_name}*? 😢",
                    parse_mode="Markdown",
                    reply_markup=get_leave_confirm_keyboard()
                )
                await state.set_state(TeamLeaveConfirm.first_confirm)
                await state.update_data(team_name=team_name, team=team)
            else:
                await send_main_menu(message, state, "Ти не в команді, тож немає що покидати! 😅")
        except Exception as e:
            logger.error(f"Error initiating leave team for user {user_id}: {e}")
            await message.answer("‼️ Виникла помилка при спробі покинути команду. Спробуй ще раз!", reply_markup=get_team_menu_keyboard())
            await state.set_state(TeamMenu.main)

    @dp.message(lambda message: message.text in ["Так, впевнений(-а) ✅", "Ні, залишитись ❌"], TeamLeaveConfirm.first_confirm)
    async def process_leave_first_confirm(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        user_data = await state.get_data()
        team_name = user_data.get("team_name", "невідома команда")
        if message.text == "Так, впевнений(-а) ✅":
            await message.answer(
                f"Точно-точно впевнений(-а)? Це останній шанс покинути команду *{team_name}*! 😔",
                parse_mode="Markdown",
                reply_markup=get_leave_confirm_keyboard()
            )
            await state.set_state(TeamLeaveConfirm.second_confirm)
        else:
            team_info, _ = await get_team_info(db, user_id)
            if team_info:
                await message.answer(f"Супер, ти залишився(-лась) у команді! 😊\n{team_info}", reply_markup=get_team_menu_keyboard())
                await state.set_state(TeamMenu.main)
            else:
                await send_main_menu(message, state, "‼️ Виникла помилка при отриманні інформації про команду. Спробуй ще раз!")

    @dp.message(lambda message: message.text in ["Так, впевнений(-а) ✅", "Ні, залишитись ❌"], TeamLeaveConfirm.second_confirm)
    async def process_leave_second_confirm(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        user_data = await state.get_data()
        team_name = user_data.get("team_name", "невідома команда")
        team = user_data.get("team")
        if message.text == "Так, впевнений(-а) ✅":
            try:
                participant = db.participants.find_one({"user_id": user_id})
                if participant and participant.get("team_id"):
                    success = db.leave_team(user_id)
                    if success:
                        await send_main_menu(message, state, f"Ти успішно покинув(-ла) команду *{team_name}*! 😢")
                        if team:
                            for member_id, member in [(m_id, db.participants.find_one({"user_id": m_id})) for m_id in team["members"] if m_id != user_id]:
                                if member and "chat_id" in member:
                                    try:
                                        await bot.send_message(
                                            chat_id=member["chat_id"],
                                            text=f"Користувач *{participant['name']}* покинув(-ла) команду *{team_name}*!",
                                            parse_mode="Markdown"
                                        )
                                    except Exception as e:
                                        logger.error(f"Error sending leave notification to user {member_id}: {e}")
                                else:
                                    logger.warning(f"No chat_id found for user {member_id} in team {team_name}")
                    else:
                        await message.answer("‼️ Не вдалося покинути команду. Спробуй ще раз!", reply_markup=get_team_menu_keyboard())
                        await state.set_state(TeamMenu.main)
                else:
                    await send_main_menu(message, state, "Ти не в команді, тож немає що покидати! 😅")
            except Exception as e:
                logger.error(f"Error leaving team for user {user_id}: {e}")
                await message.answer("‼️ Виникла помилка при покиданні команди. Спробуй ще раз!", reply_markup=get_team_menu_keyboard())
                await state.set_state(TeamMenu.main)
        else:
            team_info, _ = await get_team_info(db, user_id)
            if team_info:
                await message.answer(f"Супер, ти залишився(-лась) у команді! 😊\n{team_info}", reply_markup=get_team_menu_keyboard())
                await state.set_state(TeamMenu.main)
            else:
                await send_main_menu(message, state, "‼️ Виникла помилка при отриманні інформації про команду. Спробуй ще раз!")

    @dp.message(TeamLeaveConfirm.first_confirm)
    async def process_invalid_first_confirm(message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        team_name = user_data.get("team_name", "невідома команда")
        await message.answer(
            f"Ти впевнений(-а), що хочеш покинути команду *{team_name}*? 😢\n‼️ Будь ласка, вибери один із варіантів нижче!",
            parse_mode="Markdown",
            reply_markup=get_leave_confirm_keyboard()
        )

    @dp.message(TeamLeaveConfirm.second_confirm)
    async def process_invalid_second_confirm(message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        team_name = user_data.get("team_name", "невідома команда")
        await message.answer(
            f"Точно-точно впевнений(-а)? Це останній шанс покинути команду *{team_name}*! 😔\n‼️ Будь ласка, вибери один із варіантів нижче!",
            parse_mode="Markdown",
            reply_markup=get_leave_confirm_keyboard()
        )

    @dp.message(lambda message: message.text == "Назад")
    async def process_back_from_task(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        team_info, _ = await get_team_info(db, user_id)
        if team_info:
            await message.answer(team_info, reply_markup=get_team_menu_keyboard())
            await state.set_state(TeamMenu.main)
        else:
            await send_main_menu(message, state, "‼️ Виникла помилка при отриманні інформації про команду. Спробуй ще раз!")

    @dp.message(TeamMenu.main)
    async def process_invalid_team_menu(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        team_info, _ = await get_team_info(db, user_id)
        if team_info:
            await message.answer(f"{team_info}\n‼️ Будь ласка, вибери один із варіантів нижче!", reply_markup=get_team_menu_keyboard())
        else:
            await send_main_menu(message, state, "‼️ Виникла помилка при отриманні інформації про команду. Спробуй ще раз!")