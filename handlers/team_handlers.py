import logging
import os
from aiogram import Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from states.team import TeamCreation, TeamJoin, TeamMenu, TeamLeaveConfirm
from database import Database
from handlers.cv_handlers import register_cv_handlers
import config

logger = logging.getLogger(__name__)

def get_main_menu_keyboard(is_participant=False, event_state=None):
    if event_state == "main_task" and is_participant:
        buttons = [
            [KeyboardButton(text="CTF завдання 🚩"), KeyboardButton(text="Моя команда 🫱🏻‍🫲🏿")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="Інформація про CTF 🚩"), KeyboardButton(text="Хто такі BEST Lviv❓")],
            [KeyboardButton(text="Моя команда 🫱🏻‍🫲🏿")]
        ]
    logger.info(f"get_main_menu_keyboard called with is_participant={is_participant}, event_state={event_state}")
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_main_menu_message(is_participant=False, event_state=None):
    if is_participant:
        if event_state == "main_task":
            return (
                "Тепер ти можеш:\n"
                " ✅ Виконати основне CTF завдання\n"
                " ✅ Переглянути інформацію про свою команду\n\n"
                "Якщо хочеш поспілкуватися з іншими учасниками — пірнай у <a href=\"https://t.me/+6RoHfTot8jdkYzAy\">Чат учасників</a>."
            )
        return (
            "Повертаємось до головного меню! 😊\n"
            "Тепер ти можеш:\n"
            " ✅ Перейти до меню команди\n"
            " ✅ Дізнатись усе про подію ℹ️\n\n"
            "Якщо хочеш поспілкуватися з тими, хто вже пройшов тестове завдання — пірнай у <a href=\"https://t.me/+6RoHfTot8jdkYzAy\">Чат учасників</a>."
        )
    return (
        "Повертаємось до головного меню! 😊\n"
        "Тепер ти можеш:\n"
        " ✅ Увійти в команду чи створити свою\n"
        " ✅ Дізнатись усе про подію ℹ️\n\n"
        "Якщо не маєш команди, з якою хочеш брати участь — пірнай у <a href=\"https://t.me/+naYHbnNbN-9mYTFi\">Знайди команду</a>."
    )

def get_team_menu_keyboard(is_participant=False, test_task_status=False, event_state=None):
    logger.info(f"get_team_menu_keyboard called with is_participant={is_participant}, test_task_status={test_task_status}, event_state={event_state}")
    buttons = []
    if event_state == "main_task" and is_participant and test_task_status:
        buttons.append([KeyboardButton(text="🏆 Моє CV")])
    else:
        buttons.append([KeyboardButton(text="🧪 Тестове завдання")])
        buttons.append([KeyboardButton(text="🏆 Моє CV")])
        buttons.append([KeyboardButton(text="🚪 Покинути команду")])
    buttons.append([KeyboardButton(text="Повернутися до головного меню")])
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_leave_confirm_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Так, впевнений(-а) ✅")],
            [KeyboardButton(text="Ні, залишитись ❌")]
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

async def send_main_menu(message: types.Message, state: FSMContext, db: Database, error_message: str = None):
    user_id = message.from_user.id
    event_state = db.get_event_state()
    logger.info(f"send_main_menu called with event_state={event_state}, user_id={user_id}")
    if event_state == "finished":
        await message.answer(
            "Реєстрація та змагання завершені. Дякуємо за участь! 🚩\nЧекаємо вас на BEST CTF 2026! 😎",
            reply_markup=None
        )
        await state.clear()
        return

    participant = db.participants.find_one({"user_id": user_id})
    is_participant = False
    if participant and participant.get("team_id"):
        team_status = db.get_team_status(participant["team_id"])
        logger.info(f"Team status for user {user_id}: {team_status}")
        is_participant = team_status["is_participant"]
        if event_state in ["test_task", "main_task"] and not team_status["test_task_status"]:
            await message.answer(
                "Шкода, але ваша команда не пройшла на змагання. 😢\n"
                "Не переймайтеся, наступного року також буде CTF! 🚩\n"
                "Наша команда дуже вдячна, що саме ви захотіли бути частиною нашого івенту! 🙌",
                reply_markup=get_main_menu_keyboard(is_participant=False, event_state=event_state)
            )
            await state.clear()
            return

    if error_message:
        await message.answer(error_message, reply_markup=get_main_menu_keyboard(is_participant, event_state), parse_mode="HTML")
    else:
        await message.answer(get_main_menu_message(is_participant, event_state), reply_markup=get_main_menu_keyboard(is_participant, event_state), parse_mode="HTML")
    await state.clear()

def get_team_creation_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Повернутися до головного меню")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_confirm_data_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Правильно ✅")],
            [KeyboardButton(text="Неправильно ❌")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def register_team_handlers(dp: Dispatcher, db: Database, bot):
    register_cv_handlers(dp, db, bot)

    @dp.message(lambda message: message.text == "Моя команда 🫱🏻‍🫲🏿" and db.is_user_registered(message.from_user.id))
    async def process_team(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        event_state = db.get_event_state()
        logger.info(f"process_team called for user {user_id}, event_state={event_state}")
        if event_state == "finished":
            await message.answer(
                "Реєстрація та змагання завершені. Дякуємо за участь! 🚩\nЧекаємо вас на BEST CTF 2026! 😎",
                reply_markup=None
            )
            await state.clear()
            return

        team_info, team = await get_team_info(db, user_id)
        if team_info:
            team_status = db.get_team_status(team["_id"])
            logger.info(f"Team status in process_team: {team_status}")
            if event_state in ["test_task", "main_task"] and not team_status["test_task_status"]:
                await message.answer(
                    "Шкода, але ваша команда не пройшла на змагання. 😢\n"
                    "Не переймайтеся, наступного року також буде CTF! 🚩\n"
                    "Наша команда дуже вдячна, що саме ви захотіли бути частиною нашого івенту! 🙌",
                    reply_markup=get_main_menu_keyboard(is_participant=False, event_state=event_state)
                )
                await state.clear()
                return
            await message.answer(team_info, reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state))
            await state.set_state(TeamMenu.main)
        else:
            if event_state != "registration":
                await message.answer(
                    "Реєстрація завершена, дякуємо за інтерес! Спробуйте наступного року. 🚩",
                    reply_markup=get_main_menu_keyboard(is_participant=False, event_state=event_state)
                )
                await state.clear()
                return
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

            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="👉 Чат учасників 💭")],
                    [KeyboardButton(text="Створити команду 🫱🏻‍🫲🏿")],
                    [KeyboardButton(text="Приєднатись до команди 👥")],
                    [KeyboardButton(text="Повернутися до головного меню")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await message.answer(
                "❌ Ти поки не в команді.\n\n"
                "Але це не страшно, адже у нас є чат <a href=\"https://t.me/+naYHbnNbN-9mYTFi\">Знайди команду</a>, де можна познайомитись із тими, хто так само шукає собі мейтів, "
                "все що тобі потрібно це перейти в чат і представитись! Хто знає, може саме з цими людьми "
                "ви зійдете на п’єдестал! 🤝\n\n"
                "Або ж створи свою команду і запроси інших героїв просто зараз:",
                reply_markup=keyboard,
                parse_mode="HTML"
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
                await message.answer_photo(photo=photo, caption="💭 Приєднуйся до чату!")
            except Exception as e:
                logger.error(f"Failed to send chat.png: {str(e)}")
                await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")
        
        await message.answer(
            f"Переходь у <a href=\"https://t.me/+naYHbnNbN-9mYTFi\">Знайди команду</a>! 🤝",
            reply_markup=get_main_menu_keyboard(is_participant=False, event_state=db.get_event_state()),
            parse_mode="HTML"
        )

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, lambda message: message.text == "👉 Чат учасників 💭")
    async def process_invalid_media_chat_link(message: types.Message):
        image_path = os.path.join(config.ASSETS_PATH, "chat.png")
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at {image_path}")
            await message.answer("‼️ Виникла помилка: зображення chat.png не знайдено. Але не хвилюйся, продовжимо!")
        else:
            try:
                photo = FSInputFile(path=image_path)
                await message.answer_photo(photo=photo, caption="💭 Приєднуйся до чату!")
            except Exception as e:
                logger.error(f"Failed to send chat.png: {str(e)}")
                await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")
        await message.answer(
            "‼️ Будь ласка, надсилай тільки текст або натискай на кнопки! Не стікери, фото, GIF чи відео."
        )
        await message.answer(
            f"Переходь у <a href=\"https://t.me/+naYHbnNbN-9mYTFi\">Знайди команду</a>! 🤝",
            reply_markup=get_main_menu_keyboard(is_participant=False, event_state=db.get_event_state()),
            parse_mode="HTML"
        )

    @dp.message(lambda message: message.text == "Створити команду 🫱🏻‍🫲🏿")
    async def process_create_team(message: types.Message, state: FSMContext):
        if db.get_event_state() != "registration":
            await message.answer(
                "Реєстрація завершена, дякуємо за інтерес! Спробуйте наступного року. 🚩",
                reply_markup=get_main_menu_keyboard(is_participant=False, event_state=db.get_event_state())
            )
            await state.clear()
            return
        if db.is_user_in_team(message.from_user.id):
            await message.answer(
                "Ти вже в команді! Спочатку покинь поточну команду, щоб створити нову.",
                reply_markup=get_main_menu_keyboard(is_participant=False, event_state=db.get_event_state())
            )
            return
        await message.answer("Круто! Давай у кілька натисків по клавіатурі створимо місце, де збираються сильні💪\n\nВведи назву команди:", reply_markup=get_team_creation_keyboard())
        await state.set_state(TeamCreation.team_name)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, TeamCreation.team_name)
    async def process_invalid_media_team_name(message: types.Message, state: FSMContext):
        await message.answer("♦️ Введи назву команди:\n‼️ Будь ласка, надсилай тільки текст! Не стікери, фото, GIF чи відео.", reply_markup=get_team_creation_keyboard())
        return

    @dp.message(TeamCreation.team_name)
    async def process_team_name(message: types.Message, state: FSMContext):
        if message.text == "Повернутися до головного меню":
            await send_main_menu(message, state, db)
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

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, TeamCreation.team_password)
    async def process_invalid_media_team_password(message: types.Message, state: FSMContext):
        await message.answer("♦️ Вигадай пароль для команди. Знаю, це складно, але воно точно того варте! 🔒\n‼️ Будь ласка, надсилай тільки текст! Не стікери, фото, GIF чи відео.", reply_markup=get_team_creation_keyboard())
        return

    @dp.message(TeamCreation.team_password)
    async def process_team_password(message: types.Message, state: FSMContext):
        if message.text == "Повернутися до головного меню":
            await send_main_menu(message, state, db)
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

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, TeamCreation.confirm_data)
    async def process_invalid_media_confirm_data(message: types.Message, state: FSMContext):
        user_data = await state.get_data()
        await message.answer(
            f"Перевір, чи правильно введено дані:\nНазва команди: {user_data['team_name']}\nПароль: {user_data['team_password']}\n‼️ Будь ласка, натискай на кнопки! Не надсилай стікери, фото, GIF чи відео.",
            reply_markup=get_confirm_data_keyboard()
        )
        return

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
                        reply_markup=get_team_menu_keyboard(is_participant=False, test_task_status=False, event_state=db.get_event_state())
                    )
                    await state.set_state(TeamMenu.main)
                else:
                    await send_main_menu(message, state, db, "Цей пароль уже зайнятий, давай інший 😜")
            except Exception as e:
                logger.error(f"Error creating team for user {user_id}: {e}")
                await send_main_menu(message, state, db, "‼️ Виникла помилка при створенні команди. Спробуй ще раз!")
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
        if db.get_event_state() != "registration":
            await message.answer(
                "Реєстрація завершена, дякуємо за інтерес! Спробуйте наступного року. 🚩",
                reply_markup=get_main_menu_keyboard(is_participant=False, event_state=db.get_event_state())
            )
            await state.clear()
            return
        if db.is_user_in_team(message.from_user.id):
            await message.answer(
                "Ти вже в команді! Спочатку покинь поточну команду, щоб приєднатися до іншої.",
                reply_markup=get_main_menu_keyboard(is_participant=False, event_state=db.get_event_state())
            )
            return
        await message.answer(
            "Зібрався з силами? Приєднуйся до своєї команди! 💪\n\nВведи назву команди:",
            reply_markup=get_team_creation_keyboard()
        )
        await state.set_state(TeamJoin.team_name)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, TeamJoin.team_name)
    async def process_invalid_media_join_team_name(message: types.Message, state: FSMContext):
        await message.answer("♦️ Введи назву команди:\n‼️ Будь ласка, надсилай тільки текст! Не стікери, фото, GIF чи відео.", reply_markup=get_team_creation_keyboard())
        return

    @dp.message(TeamJoin.team_name)
    async def process_join_team_name(message: types.Message, state: FSMContext):
        if message.text == "Повернутися до головного меню":
            await send_main_menu(message, state, db)
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

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, TeamJoin.team_password)
    async def process_invalid_media_join_team_password(message: types.Message, state: FSMContext):
        await message.answer("♦️ Введи пароль команди. Ти ж його знаєш, правда? 😅\n‼️ Будь ласка, надсилай тільки текст! Не стікери, фото, GIF чи відео.", reply_markup=get_team_creation_keyboard())
        return

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
                    reply_markup=get_team_menu_keyboard(is_participant=False, test_task_status=False, event_state=db.get_event_state())
                )
                await state.set_state(TeamMenu.main)
                for member_id, member in [(m_id, db.participants.find_one({"user_id": m_id})) for m_id in team["members"] if m_id != user_id]:
                    if member and "chat_id" in member:
                        try:
                            await bot.send_message(
                                chat_id=member["chat_id"],
                                text=f"Вітаю, до вашої команди *{team_name}* доєднався(-лась) *{new_member_name}*! Якщо ви не знаете, хто це, зверніться до {config.ORGANIZER_CONTACT}.",
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

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, lambda message: message.text == "Повернутися до головного меню")
    async def process_invalid_media_back_to_main_menu(message: types.Message, state: FSMContext):
        await message.answer("‼️ Будь ласка, надсилай тільки текст або натискай на кнопки! Не стікери, фото, GIF чи відео.")
        await send_main_menu(message, state, db)

    @dp.message(lambda message: message.text == "Повернутися до головного меню")
    async def process_back_to_main_menu(message: types.Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state in [TeamCreation.team_name, TeamCreation.team_password, TeamJoin.team_name, TeamJoin.team_password, TeamLeaveConfirm.first_confirm]:
            await send_main_menu(message, state, db)
        else:
            await send_main_menu(message, state, db)

    @dp.message(lambda message: message.text == "🧪 Тестове завдання", TeamMenu.main)
    async def process_test_task(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        event_state = db.get_event_state()
        logger.info(f"process_test_task called for user {user_id}, event_state={event_state}")
        team_info, team = await get_team_info(db, user_id)
        if not team:
            await send_main_menu(message, state, db, "Ви не в команді! Приєднайтесь до команди або створіть нову.")
            return
        team_status = db.get_team_status(team["_id"])
        logger.info(f"Team status in process_test_task: {team_status}")
        if event_state == "registration":
            image_path = os.path.join(config.ASSETS_PATH, "test.png")
            if not os.path.exists(image_path):
                logger.error(f"Image file not found at {image_path}")
                await message.answer("‼️ Виникла помилка: зображення test.png не знайдено. Але не хвилюйся, продовжимо!")
            else:
                try:
                    photo = FSInputFile(path=image_path)
                    await message.answer_photo(photo=photo, caption="🧪 Тестове завдання для вашої команди!")
                except Exception as e:
                    logger.error(f"Failed to send test.png: {str(e)}")
                    await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")
            await message.answer(
                "Йой його поки тут немає😢 Воно буде 15-го листопада. Заряджай ноут, завантажуй усі словники і будь готовий до бою🔥\n"
                "‼️ Увага ‼️: брати участь можуть лише команди, у яких є щонайменше 3 учасники.",
                reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
            )
        elif event_state == "test_task" and team_status["test_task_status"]:
            image_path = os.path.join(config.ASSETS_PATH, "test.png")
            if not os.path.exists(image_path):
                logger.error(f"Image file not found at {image_path}")
                await message.answer("‼️ Виникла помилка: зображення test.png не знайдено. Але не хвилюйся, продовжимо!")
            else:
                try:
                    photo = FSInputFile(path=image_path)
                    await message.answer_photo(photo=photo, caption="🧪 Тестове завдання для вашої команди!")
                except Exception as e:
                    logger.error(f"Failed to send test.png: {str(e)}")
                    await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")
            pdf_path = os.path.join(config.ASSETS_PATH, "test_task.pdf")
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found at {pdf_path}")
                await message.answer("‼️ Виникла помилка: файл test_task.pdf не знайдено. Але не хвилюйся, продовжимо!")
            else:
                try:
                    document = FSInputFile(path=pdf_path)
                    await message.answer_document(document=document, caption="🧪 Тестове завдання для вашої команди!")
                except Exception as e:
                    logger.error(f"Failed to send test_task.pdf: {str(e)}")
                    await message.answer(f"‼️ Виникла помилка при відправці файлу: {str(e)}. Але не хвилюйся, продовжимо!")
            await message.answer(
                "Це ваше тестове завдання! 🧪\n"
                "Виконайте його та надішліть відповідь організаторам.",
                reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
            )
        else:
            await message.answer(
                "Тестовий етап ще не розпочався або вже закінчився. Слідкуй за оновленнями! 🚩",
                reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
            )

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, lambda message: message.text == "🧪 Тестове завдання", TeamMenu.main)
    async def process_invalid_media_test_task(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        event_state = db.get_event_state()
        logger.info(f"process_invalid_media_test_task called for user {user_id}, event_state={event_state}")
        team_info, team = await get_team_info(db, user_id)
        if not team:
            await send_main_menu(message, state, db, "Ви не в команді! Приєднайтесь до команди або створіть нову.")
            return
        team_status = db.get_team_status(team["_id"])
        logger.info(f"Team status in process_invalid_media_test_task: {team_status}")
        await message.answer("‼️ Будь ласка, надсилай тільки текст або натискай на кнопки! Не стікери, фото, GIF чи відео.")
        if event_state == "registration":
            image_path = os.path.join(config.ASSETS_PATH, "test.png")
            if not os.path.exists(image_path):
                logger.error(f"Image file not found at {image_path}")
                await message.answer("‼️ Виникла помилка: зображення test.png не знайдено. Але не хвилюйся, продовжимо!")
            else:
                try:
                    photo = FSInputFile(path=image_path)
                    await message.answer_photo(photo=photo, caption="🧪 Тестове завдання для вашої команди!")
                except Exception as e:
                    logger.error(f"Failed to send test.png: {str(e)}")
                    await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")
            await message.answer(
                "Йой його поки тут немає😢 Воно буде 15-го листопада. Заряджай ноут, завантажуй усі словники і будь готовий до бою🔥\n"
                "‼️ Увага ‼️: брати участь можуть лише команди, у яких є щонайменше 3 учасники.",
                reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
            )
        elif event_state == "test_task" and team_status["test_task_status"]:
            image_path = os.path.join(config.ASSETS_PATH, "test.png")
            if not os.path.exists(image_path):
                logger.error(f"Image file not found at {image_path}")
                await message.answer("‼️ Виникла помилка: зображення test.png не знайдено. Але не хвилюйся, продовжимо!")
            else:
                try:
                    photo = FSInputFile(path=image_path)
                    await message.answer_photo(photo=photo, caption="🧪 Тестове завдання для вашої команди!")
                except Exception as e:
                    logger.error(f"Failed to send test.png: {str(e)}")
                    await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")
            pdf_path = os.path.join(config.ASSETS_PATH, "test_task.pdf")
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found at {pdf_path}")
                await message.answer("‼️ Виникла помилка: файл test_task.pdf не знайдено. Але не хвилюйся, продовжимо!")
            else:
                try:
                    document = FSInputFile(path=pdf_path)
                    await message.answer_document(document=document, caption="🧪 Тестове завдання для вашої команди!")
                except Exception as e:
                    logger.error(f"Failed to send test_task.pdf: {str(e)}")
                    await message.answer(f"‼️ Виникла помилка при відправці файлу: {str(e)}. Але не хвилюйся, продовжимо!")
            await message.answer(
                "Це ваше тестове завдання! 🧪\n"
                "Виконайте його та надішліть відповідь організаторам.",
                reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
            )
        else:
            await message.answer(
                "Тестовий етап ще не розпочався або вже закінчився. Слідкуй за оновленнями! 🚩",
                reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
            )

    @dp.message(lambda message: message.text == "🚩 CTF завдання 🚩", TeamMenu.main)
    async def process_main_task(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        event_state = db.get_event_state()
        logger.info(f"process_main_task called for user {user_id}, event_state={event_state}")
        team_info, team = await get_team_info(db, user_id)
        if not team:
            await send_main_menu(message, state, db, "Ви не в команді! Приєднайтесь до команди або створіть нову.")
            return
        team_status = db.get_team_status(team["_id"])
        logger.info(f"Team status in process_main_task: {team_status}")
        if not team_status["is_participant"] or not team_status["test_task_status"]:
            await message.answer(
                "Ваша команда ще не пройшла тестове завдання. Завершіть його, щоб отримати доступ до основного CTF завдання! 🚩",
                reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
            )
            return
        if event_state != "main_task":
            await message.answer(
                "Основний етап CTF ще не розпочався або вже закінчився. Слідкуй за оновленнями! 🚩",
                reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
            )
            return
        pdf_path = os.path.join(config.ASSETS_PATH, "main_task.pdf")
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found at {pdf_path}")
            await message.answer("‼️ Виникла помилка: файл main_task.pdf не знайдено. Зверніться до організаторів!")
        else:
            try:
                document = FSInputFile(path=pdf_path)
                await message.answer_document(document=document, caption="🚩 Основне CTF завдання для вашої команди!")
            except Exception as e:
                logger.error(f"Failed to send main_task.pdf: {str(e)}")
                await message.answer(f"‼️ Виникла помилка при відправці файлу: {str(e)}. Зверніться до організаторів!")
        await message.answer(
            "Це ваше основне CTF завдання! Виконайте його та надішліть відповідь організаторам.",
            reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
        )

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, lambda message: message.text == "🚩 CTF завдання 🚩", TeamMenu.main)
    async def process_invalid_media_main_task(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        event_state = db.get_event_state()
        logger.info(f"process_invalid_media_main_task called for user {user_id}, event_state={event_state}")
        team_info, team = await get_team_info(db, user_id)
        if not team:
            await send_main_menu(message, state, db, "Ви не в команді! Приєднайтесь до команди або створіть нову.")
            return
        team_status = db.get_team_status(team["_id"])
        logger.info(f"Team status in process_invalid_media_main_task: {team_status}")
        if not team_status["is_participant"] or not team_status["test_task_status"]:
            await message.answer(
                "Ваша команда ще не пройшла тестове завдання. Завершіть його, щоб отримати доступ до основного CTF завдання! 🚩",
                reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
            )
            return
        if event_state != "main_task":
            await message.answer(
                "Основний етап CTF ще не розпочався або вже закінчився. Слідкуй за оновленнями! 🚩",
                reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
            )
            return
        await message.answer("‼️ Будь ласка, надсилай тільки текст або натискай на кнопки! Не стікери, фото, GIF чи відео.")
        pdf_path = os.path.join(config.ASSETS_PATH, "main_task.pdf")
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found at {pdf_path}")
            await message.answer("‼️ Виникла помилка: файл main_task.pdf не знайдено. Зверніться до організаторів!")
        else:
            try:
                document = FSInputFile(path=pdf_path)
                await message.answer_document(document=document, caption="🚩 Основне CTF завдання для вашої команди!")
            except Exception as e:
                logger.error(f"Failed to send main_task.pdf: {str(e)}")
                await message.answer(f"‼️ Виникла помилка при відправці файлу: {str(e)}. Зверніться до організаторів!")
        await message.answer(
            "Це ваше основне CTF завдання! Виконайте його та надішліть відповідь організаторам.",
            reply_markup=get_team_menu_keyboard(team_status["is_participant"], team_status["test_task_status"], event_state)
        )

    @dp.message(lambda message: message.text == "🚪 Покинути команду", TeamMenu.main)
    async def process_leave_team(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        team_info, team = await get_team_info(db, user_id)
        if not team:
            await send_main_menu(message, state, db, "Ви не в команді! Приєднайтесь до команди або створіть нову.")
            return
        await message.answer(
            f"Ти впевнений(-а), що хочеш покинути команду *{team['team_name']}*? 😔",
            parse_mode="Markdown",
            reply_markup=get_leave_confirm_keyboard()
        )
        await state.set_state(TeamLeaveConfirm.first_confirm)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, TeamLeaveConfirm.first_confirm)
    async def process_invalid_media_leave_confirm(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        team_info, team = await get_team_info(db, user_id)
        if not team:
            await send_main_menu(message, state, db, "Ви не в команді! Приєднайтесь до команди або створіть нову.")
            return
        await message.answer(
            f"‼️ Будь ласка, натискай на кнопки! Не надсилай стікери, фото, GIF чи відео.\n"
            f"Ти впевнений(-а), що хочеш покинути команду *{team['team_name']}*? 😔",
            parse_mode="Markdown",
            reply_markup=get_leave_confirm_keyboard()
        )

    @dp.message(lambda message: message.text in ["Так, впевнений(-а) ✅", "Ні, залишитись ❌"], TeamLeaveConfirm.first_confirm)
    async def process_leave_confirm(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        team_info, team = await get_team_info(db, user_id)
        if not team:
            await send_main_menu(message, state, db, "Ви не в команді! Приєднайтесь до команди або створіть нову.")
            return
        if message.text == "Так, впевнений(-а) ✅":
            try:
                success = db.leave_team(user_id)
                if success:
                    await message.answer(
                        f"Ти покинув(-ла) команду *{team['team_name']}*. 😢\n"
                        "Але не хвилюйся, ти можеш створити нову або приєднатися до іншої!",
                        parse_mode="Markdown",
                        reply_markup=get_main_menu_keyboard(is_participant=False, event_state=db.get_event_state())
                    )
                    for member_id, member in [(m_id, db.participants.find_one({"user_id": m_id})) for m_id in team["members"] if m_id != user_id]:
                        if member and "chat_id" in member:
                            try:
                                await bot.send_message(
                                    chat_id=member["chat_id"],
                                    text=f"Учасник залишив команду *{team['team_name']}*. 😔",
                                    parse_mode="Markdown"
                                )
                            except Exception as e:
                                logger.error(f"Error sending notification to user {member_id}: {e}")
                    await state.clear()
                else:
                    await send_main_menu(message, state, db, "‼️ Виникла помилка при виході з команди. Спробуй ще раз!")
            except Exception as e:
                logger.error(f"Error leaving team for user {user_id}: {e}")
                await send_main_menu(message, state, db, "‼️ Виникла помилка при виході з команди. Спробуй ще раз!")
        else:
            team_status = db.get_team_status(team["_id"])
            await message.answer(
                "Чудово, ти залишився(-лась) у команді! 💪",
                reply_markup=get_team_menu_keyboard(is_participant=team_status["is_participant"], test_task_status=team_status["test_task_status"], event_state=db.get_event_state())
            )
            await state.set_state(TeamMenu.main)