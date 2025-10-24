import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from states.registration import Registration
from config import ADMIN_ID, MONGODB_URI
import config
from database import Database
from handlers.info_ctf_handlers import register_info_ctf_handlers
from handlers.info_best_handlers import register_info_best_handlers
from handlers.team_handlers import register_team_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UNIVERSITIES = ["🎓 НУЛП", "🎓 ЛНУ", "🎓 НЛТУ", "🎓 IT STEP", "🎓 УКУ", "Інший"]
COURSES = ["1 курс 🤓", "2 курс 🤓", "3 курс 🤓", "4 курс 🤓", "Магістратура 🤓", "Аспірантура 🤓"]
MAIN_MENU_MESSAGES = [
    "Вітаю, чемпіоне! Ти щойно потрапив у світ загадок і експлойтів BEST CTF! 🚩",
    "Ласкаво просимо на BEST CTF! Твої пригоди починаються тут.😉",
    "Йо-хо-хо! І флаг у кишеню! Лет’s гоу! 🚩",
    "Сезон полювання за байтами “BEST CTF 2025” відкрито! Покажи себе🔥",
    "Увага, увага! У гру заходить новий претендент на чемпіонський кубок BEST CTF. 😎"
]
COMPLIMENTS = [
    "Ооо! У мене якось був кіт із таким іменем 😁",
    "Бачила зранку твоє ім’я в гороскопі. Кажуть, такі люди сьогодні на правильному шляху 🫡",
    "Круто! Не чула цього імені, відколи динозаври вимерли 😧",
    "Чесно? Це дуже круто 😎",
    "Ха-ха-ха. Нарешті..... ти думав(ла) я тебе не знайду, {}?"
]

def get_main_menu_keyboard(is_participant=False, event_state=None):
    if event_state == "main_task" and is_participant:
        buttons = [
            [KeyboardButton(text="🚩 CTF завдання"), KeyboardButton(text="Моя команда 🫱🏻‍🫲🏿")]
        ]
    else:
        buttons = [
            [KeyboardButton(text="Інформація про CTF 🚩"), KeyboardButton(text="Хто такі BEST Lviv❓")],
            [KeyboardButton(text="Моя команда 🫱🏻‍🫲🏿")]
        ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_unregistered_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Зареєструватись у CTF-2025! 📝")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_universities_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=uni) for uni in UNIVERSITIES[i:i + 2]] for i in range(0, len(UNIVERSITIES), 2)],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_courses_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=course) for course in COURSES[i:i + 2]] for i in range(0, len(COURSES), 2)],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_source_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Instagram"), KeyboardButton(text="LinkedIn")],
            [KeyboardButton(text="TikTok"), KeyboardButton(text="Друзі")],
            [KeyboardButton(text="Представники університету"), KeyboardButton(text="Живі оголошення/інфостійки")],
            [KeyboardButton(text="Інше")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поділитися контактом 📱", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_check_data_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Правильно ✅")],
            [KeyboardButton(text="Неправильно ❌")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_consent_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Погоджуюсь")],
            [KeyboardButton(text="❌ Відмовляюсь")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

async def send_main_menu(message: types.Message, state: FSMContext, db: Database, registered: bool = False, name: str = None):
    user_id = message.from_user.id
    event_state = db.get_event_state()
    if event_state == "finished":
        await message.answer(
            "Реєстрація та змагання завершені. Дякуємо за участь! 🚩\nЧекаємо вас на BEST CTF 2026! 😎",
            reply_markup=None
        )
        await state.clear()
        return

    if registered:
        participant = db.participants.find_one({"user_id": user_id})
        is_participant = False
        if participant and participant.get("team_id"):
            team_status = db.get_team_status(participant["team_id"])
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

        keyboard = get_main_menu_keyboard(is_participant, event_state)
        if is_participant:
            if event_state == "main_task":
                await message.answer(
                    "Тепер ти можеш:\n"
                    " ✅ Виконати основне CTF завдання\n"
                    " ✅ Переглянути інформацію про свою команду\n\n"
                    "Якщо хочеш поспілкуватися з іншими учасниками — пірнай у <a href=\"https://t.me/+6RoHfTot8jdkYzAy\">Чат учасників</a>.",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    "Тепер ти можеш:\n"
                    " ✅ Перейти до меню команди\n"
                    " ✅ Дізнатись усе про подію ℹ️\n\n"
                    "Якщо хочеш поспілкуватися з тими, хто вже пройшов тестове завдання — пірнай у <a href=\"https://t.me/+6RoHfTot8jdkYzAy\">Чат учасників</a>.",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        else:
            await message.answer(
                "Тепер ти можеш:\n"
                " ✅ Увійти в команду чи створити свою\n"
                " ✅ Дізнатись усе про подію ℹ️\n\n"
                "Якщо не маєш команди, з якою хочеш брати участь — пірнай у <a href=\"https://t.me/+naYHbnNbN-9mYTFi\">Знайди команду</a>.",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        await message.answer(random.choice(MAIN_MENU_MESSAGES))
    else:
        if event_state != "registration":
            await message.answer(
                "Реєстрація завершена, дякуємо за інтерес! Спробуйте наступного року. 🚩",
                reply_markup=None
            )
        else:
            await message.answer(
                "🚩 Ласкаво просимо до CTF-2025! 🚩\n"
                "  Немає часу зволікати. Дій! ⚡️\n"
                "  Спочатку зареєструйся як учасник, а потім створи або приєднайся до команди! 🤝",
                reply_markup=get_unregistered_keyboard()
            )
    await state.clear()

def register_user_handlers(dp: Dispatcher, db: Database, bot: Bot):
    register_team_handlers(dp, db, bot)
    register_info_ctf_handlers(dp, db, bot)
    register_info_best_handlers(dp, db, bot)

    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        await state.clear()  
        if db.is_user_registered(user_id):
            name = db.get_user_data(user_id)
            await send_main_menu(message, state, db, registered=True, name=name)
        else:
            await send_main_menu(message, state, db)

    @dp.message(lambda message: message.text == "🚩 CTF завдання" and db.get_event_state() == "main_task")
    async def process_main_task(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        event_state = db.get_event_state()
        logger.info(f"process_main_task called for user {user_id}, event_state={event_state}")
        participant = db.participants.find_one({"user_id": user_id})
        if not participant or not participant.get("team_id"):
            await message.answer(
                "Ви не в команді! Приєднайтесь до команди, щоб отримати доступ до CTF завдання. 🚩",
                reply_markup=get_main_menu_keyboard(is_participant=False, event_state=event_state)
            )
            return
        team_status = db.get_team_status(participant["team_id"])
        if not team_status["is_participant"] or not team_status["test_task_status"]:
            await message.answer(
                "Ваша команда ще не пройшла тестове завдання. Завершіть його, щоб отримати доступ до основного CTF завдання! 🚩",
                reply_markup=get_main_menu_keyboard(is_participant=False, event_state=event_state)
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
            reply_markup=get_main_menu_keyboard(is_participant=True, event_state=event_state)
        )

    @dp.message(lambda message: message.text == "Зареєструватись у CTF-2025! 📝")
    async def process_register(message: types.Message, state: FSMContext):
        if db.get_event_state() != "registration":
            await message.answer(
                "Реєстрація завершена, дякуємо за інтерес! Спробуйте наступного року. 🚩",
                reply_markup=None
            )
            return
        if db.is_user_registered(message.from_user.id):
            name = db.get_user_data(message.from_user.id)
            await send_main_menu(message, state, db, registered=True, name=name)
            return
        image_path = os.path.join(config.ASSETS_PATH, "register.png")
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at {image_path}")
            await message.answer("‼️ Виникла помилка: зображення register.png не знайдено. Але не хвилюйся, продовжимо реєстрацію!")
        else:
            try:
                photo = FSInputFile(path=image_path)
                await message.answer_photo(photo=photo, caption="🚩 Починаємо реєстрацію в CTF-2025! 🚩")
            except Exception as e:
                logger.error(f"Failed to send register.png: {str(e)}")
                await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо реєстрацію!")
        await message.answer("♦️ Введи своє ім'я:")
        await state.set_state(Registration.name)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.name)
    async def process_invalid_media_name(message: types.Message, state: FSMContext):
        await message.answer("♦️ Введи своє ім'я:\n‼️ Будь ласка, надсилай тільки текст! Не стікери, фото, GIF чи відео.")
        return

    @dp.message(Registration.name)
    async def process_name(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("♦️ Введи своє ім'я:\n‼️ Будь ласка, надсилай тільки текст! Не фото, гіфки, стікери чи голосові повідомлення.")
            return
        name = message.text.strip()
        if not (name.replace(" ", "").isalpha() and len(name.replace(" ", "")) >= 2):
            await message.answer("♦️ Введи своє ім'я:\n‼️ Упс, я не думаю, що твоє ім’я - набір цифр чи однобуквений нік. 😏 Спробуй ще!")
            return
        await state.update_data(name=name)
        await message.answer(COMPLIMENTS[-1].format(name) if random.random() > 0.2 else random.choice(COMPLIMENTS[:-1]))
        await message.answer("Про таке не дуже гарно питати, але все ж 😅 \n♦️ Скільки тобі років? :")
        await state.set_state(Registration.age)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.age)
    async def process_invalid_media_age(message: types.Message, state: FSMContext):
        await message.answer("♦️ Скільки тобі років? :\n‼️ Будь ласка, надсилай тільки текст! Не стікери, фото, GIF чи відео.")
        return

    @dp.message(Registration.age)
    async def process_age(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("♦️ Скільки тобі років? :\n‼️ Будь ласка, надсилай тільки текст! Не фото, гіфки, стікери чи голосові повідомлення.")
            return
        age_text = message.text.strip()
        if not age_text.isdigit() or not 16 <= int(age_text) <= 50:
            await message.answer("♦️ Скільки тобі років? :\n‼️ Упс, вік має бути числом від 16 😄. Спробуй ще раз 😏:")
            return
        await state.update_data(age=int(age_text))
        await message.answer(f"{age_text} - поважна цифра 🧐. Скоро з тобою підемо на пенсію")
        await message.answer("📌 Май на увазі, участь у наших змаганнях можуть брати лише поточні студенти.\n\n")
        await message.answer("♦️ Вибери свій університет 🎓 або введи власний:", reply_markup=get_universities_keyboard())
        await state.set_state(Registration.university)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.university)
    async def process_invalid_media_university(message: types.Message, state: FSMContext):
        await message.answer("♦️ Вибери свій університет 🎓 або введи власний:\n‼️ Будь ласка, надсилай тільки текст або натискай на кнопки! Не стікери, фото, GIF чи відео.", reply_markup=get_universities_keyboard())
        return

    @dp.message(Registration.university)
    async def process_university(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("♦️ Вибери свій університет 🎓 або введи власний:\n‼️ Будь ласка, вибери варіант із кнопок або введи текст!", reply_markup=get_universities_keyboard())
            return
        if message.text == "Інший":
            await message.answer("Ого, ти з унікального місця! 😄 Введи назву свого університету:")
            await state.set_state(Registration.new_university)
        else:
            university = message.text.replace("🎓 ", "") if message.text in UNIVERSITIES else message.text.strip()
            if len(university) < 2:
                await message.answer("♦️ Введи коректну назву університету (не менше 2 символів)! 😅")
                return
            await state.update_data(university=university)
            logger.info(f"User {message.from_user.id} selected university: {university}")
            await message.answer(f"Дякую! Зареєструвала твій університет: {university} 🎓")
            await message.answer("♦️ Введи свою спеціальність:")
            await state.set_state(Registration.specialty)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.new_university)
    async def process_invalid_media_new_university(message: types.Message, state: FSMContext):
        await message.answer("♦️ Введи назву свого університету:\n‼️ Будь ласка, надсилай тільки текст! Не стікери, фото, GIF чи відео.")
        return

    @dp.message(Registration.new_university)
    async def process_new_university(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("♦️ Введи назву свого університету:\n‼️ Будь ласка, надсилай тільки текст! Не фото, гіфки, стікери чи голосові повідомлення.")
            return
        custom_university = message.text.strip()
        if len(custom_university) < 2:
            await message.answer("♦️ Введи назву свого університету:\n‼️ Упс, введи коректну назву університету (не менше 2 символів)! 😅")
            return
        await state.update_data(university=custom_university)
        logger.info(f"User {message.from_user.id} entered custom university: {custom_university}")
        await message.answer(f"Дякую! Зареєструвала твій університет: {custom_university} 🎓")
        await message.answer("📌 Знову нагадую, участь можуть брати лише поточні студенти закладу вищої освіти")
        await message.answer("♦️ Введи свою спеціальність:")
        await state.set_state(Registration.specialty)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.specialty)
    async def process_invalid_media_specialty(message: types.Message, state: FSMContext):
        await message.answer("♦️ Введи свою спеціальність:\n‼️ Будь ласка, надсилай тільки текст! Не стікери, фото, GIF чи відео.")
        return

    @dp.message(Registration.specialty)
    async def process_specialty(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("♦️ Введи свою спеціальність:\n‼️ Будь ласка, надсилай тільки текст! Не фото, гіфки, стікери чи голосові повідомлення.")
            return
        specialty = message.text.strip()
        if len(specialty) < 2:
            await message.answer("♦️ Введи свою спеціальність:\n‼️ Упс, введи коректну назву спеціальності (не менше 2 символів). 😏 Спробуй ще!")
            return
        await state.update_data(specialty=specialty)
        await message.answer("Тільки чесно, сам захотів, чи батьки відправили? 😮‍💨")
        await message.answer("♦️ Вибери свій курс 🤓:", reply_markup=get_courses_keyboard())
        await state.set_state(Registration.course)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.course)
    async def process_invalid_media_course(message: types.Message, state: FSMContext):
        await message.answer("♦️ Вибери свій курс 🤓:\n‼️ Будь ласка, натискай на кнопки! Не надсилай стікери, фото, GIF чи відео.", reply_markup=get_courses_keyboard())
        return

    @dp.message(lambda message: message.text in COURSES, Registration.course)
    async def process_course(message: types.Message, state: FSMContext):
        await state.update_data(course=message.text)
        await message.answer("♦️ Звідки ти дізнався(-лась) про змагання? 📢", reply_markup=get_source_keyboard())
        await state.set_state(Registration.source)

    @dp.message(Registration.course)
    async def process_invalid_course(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("♦️ Вибери свій курс 🤓:\n‼️ Будь ласка, натискай на кнопки! Не надсилай фото, гіфки, стікери чи голосові повідомлення.", reply_markup=get_courses_keyboard())
            return
        await message.answer("♦️ Вибери свій курс 🤓:\n‼️ Будь ласка, вибери один із варіантів нижче:", reply_markup=get_courses_keyboard())

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.source)
    async def process_invalid_media_source(message: types.Message, state: FSMContext):
        await message.answer("♦️ Звідки ти дізнався(-лась) про змагання? 📢\n‼️ Будь ласка, натискай на кнопки! Не надсилай стікери, фото, GIF чи відео.", reply_markup=get_source_keyboard())
        return

    @dp.message(lambda message: message.text in ["Instagram", "LinkedIn", "TikTok", "Друзі", "Представники університету", "Живі оголошення/інфостійки", "Інше"], Registration.source)
    async def process_source(message: types.Message, state: FSMContext):
        if message.text == "Інше":
            await message.answer("Ого, цікаво! Введи, звідки саме ти дізнався(-лась):")
            await state.set_state(Registration.custom_source)
        else:
            await state.update_data(source=message.text)
            await message.answer("Реально?? Я так само! 🥳")
            await message.answer("♦️ Поділись своїм контактом 📱 (натисни кнопку нижче)", reply_markup=get_contact_keyboard())
            await state.set_state(Registration.contact)

    @dp.message(Registration.source)
    async def process_invalid_source(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("♦️ Звідки ти дізнався(-лась) про змагання? 📢\n‼️ Будь ласка, натискай на кнопки! Не надсилай фото, гіфки, стікери чи голосові повідомлення.", reply_markup=get_source_keyboard())
            return
        await message.answer("♦️ Звідки ти дізнався(-лась) про змагання? 📢\n‼️ Будь ласка, вибери один із варіантів нижче:", reply_markup=get_source_keyboard())

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.custom_source)
    async def process_invalid_media_custom_source(message: types.Message, state: FSMContext):
        await message.answer("♦️ Введи, звідки саме ти дізнався(-лась):\n‼️ Будь ласка, надсилай тільки текст! Не стікери, фото, GIF чи відео.")
        return

    @dp.message(Registration.custom_source)
    async def process_custom_source(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("♦️ Введи, звідки саме ти дізнався(-лась):\n‼️ Будь ласка, надсилай тільки текст! Не фото, гіфки, стікери чи голосові повідомлення.")
            return
        custom_source = message.text.strip()
        if len(custom_source) < 2:
            await message.answer("♦️ Введи, звідки саме ти дізнався(-лась):\n‼️ Упс, введи коректне джерело (не менше 2 символів)! 😅")
            return
        await state.update_data(source=custom_source)
        await message.answer("Чудово, додала джерело! 🤓")
        await message.answer("♦️ Поділись своїм контактом 📱 (натисни кнопку нижче)", reply_markup=get_contact_keyboard())
        await state.set_state(Registration.contact)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.contact)
    async def process_invalid_media_contact(message: types.Message, state: FSMContext):
        await message.answer("♦️ Поділись своїм контактом 📱 (натисни кнопку нижче)\n‼️ Будь ласка, натискай на кнопки! Не надсилай стікери, фото, GIF чи відео.", reply_markup=get_contact_keyboard())
        return

    @dp.message(Registration.contact)
    async def process_contact(message: types.Message, state: FSMContext):
        if message.contact:
            await state.update_data(phone=message.contact.phone_number)
            user_data = await state.get_data()
            user_id = message.from_user.id
            required_fields = ["name", "age", "university", "specialty", "course", "source", "phone"]
            if not all(field in user_data for field in required_fields):
                logger.error(f"Incomplete data for user {user_id}: {user_data}")
                await message.answer("‼️ Виникла помилка: не всі дані заповнено. Почнімо спочатку!")
                await state.clear()
                await message.answer("♦️ Введи своє ім'я:")
                await state.set_state(Registration.name)
                return
            try:
                db.add_participant(
                    user_id,
                    user_data["name"],
                    user_data["age"],
                    user_data["university"],
                    user_data["specialty"],
                    user_data["course"],
                    user_data["source"],
                    user_data["phone"],
                    False,
                    None,
                    message.chat.id
                )
                logger.info(f"Added participant {user_id} to DB")
                await message.answer("♦️ Перед тим, як завершити реєстрацію, перевір, чи ти добре ввів(-ела) особисті дані. 😌", reply_markup=get_check_data_keyboard())
                await state.set_state(Registration.check_data)
            except Exception as e:
                logger.error(f"Failed to add participant {user_id}: {e}")
                await message.answer("‼️ Виникла помилка при збереженні даних. Спробуй ще раз!")
                await state.clear()
        else:
            if message.text:
                await message.answer("♦️ Поділись своїм контактом 📱 (натисни кнопку нижче)\n‼️ Упс, це текст, але потрібно натиснути 'Поділитися контактом'!", reply_markup=get_contact_keyboard())
            else:
                await message.answer("♦️ Поділись своїм контактом 📱 (натисни кнопку нижче)\n‼️ Будь ласка, натискай на кнопки! Не надсилай фото, гіфки, стікери чи голосові повідомлення.", reply_markup=get_contact_keyboard())

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.check_data)
    async def process_invalid_media_check_data(message: types.Message, state: FSMContext):
        await message.answer("♦️ Перед тим, як завершити реєстрацію, перевір, чи ти добре ввів(-ела) особисті дані. 😌\n‼️ Будь ласка, натискай на кнопки! Не надсилай стікери, фото, GIF чи відео.", reply_markup=get_check_data_keyboard())
        return

    @dp.message(lambda message: message.text in ["Правильно ✅", "Неправильно ❌"], Registration.check_data)
    async def process_check_data(message: types.Message, state: FSMContext):
        if message.text == "Правильно ✅":
            await message.answer("Чудово! 😊 Тепер підтверди згоду на обробку даних:", reply_markup=get_consent_keyboard())
            await state.set_state(Registration.data_consent)
        else:
            await state.clear()
            await message.answer("♦️ Введи своє ім'я:")
            await state.set_state(Registration.name)

    @dp.message(Registration.check_data)
    async def process_invalid_check_data(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("♦️ Перед тим, як завершити реєстрацію, перевір, чи ти добре ввів(-ела) особисті дані. 😌\n‼️ Будь ласка, натискай на кнопки! Не надсилай фото, гіфки, стікери чи голосові повідомлення.", reply_markup=get_check_data_keyboard())
            return
        await message.answer("♦️ Перед тим, як завершити реєстрацію, перевір, чи ти добре ввів(-ела) особисті дані. 😌\n‼️ Будь ласка, вибери одну з кнопок нижче:", reply_markup=get_check_data_keyboard())

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation, Registration.data_consent)
    async def process_invalid_media_consent(message: types.Message, state: FSMContext):
        await message.answer("♦️ Підтверди згоду на обробку даних:\n‼️ Будь ласка, натискай на кнопки! Не надсилай стікери, фото, GIF чи відео.", reply_markup=get_consent_keyboard())
        return

    @dp.message(lambda message: message.text in ["✅ Погоджуюсь", "❌ Відмовляюсь"], Registration.data_consent)
    async def process_data_consent(message: types.Message, state: FSMContext):
        if message.text == "✅ Погоджуюсь":
            user_id = message.from_user.id
            await state.update_data(data_consent=True)
            try:
                db.participants.update_one({"user_id": user_id}, {"$set": {"data_consent": True}})
                logger.info(f"Updated data_consent for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to update data_consent for user {user_id}: {e}")
                await message.answer("‼️ Виникла помилка при збереженні згоди. Спробуй ще раз!")
                await state.clear()
                return
            await message.answer("Круто! Коли буду готувати атаку на пентагон, буду знати, куди телефонувати😏")
            await send_main_menu(message, state, db, registered=True, name=(await state.get_data())["name"])
        else:
            await message.answer(
                "Наша команда збирає особисту інформацію учасників лише задля загальної статистики події 🥹\n"
                "Будемо безмежно вдячні, якщо обереш '✅ Погоджуюсь'! 😌",
                reply_markup=get_consent_keyboard()
            )

    @dp.message(Registration.data_consent)
    async def process_invalid_consent(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("♦️ Підтверди згоду на обробку даних:\n‼️ Будь ласка, натискай на кнопки! Не надсилай фото, гіфки, стікери чи голосові повідомлення.", reply_markup=get_consent_keyboard())
            return
        await message.answer("♦️ Підтверди згоду на обробку даних:\n‼️ Будь ласка, вибери одну з кнопок нижче:", reply_markup=get_consent_keyboard())

    @dp.message(lambda message: message.text == "Ще раз зареєструватися 📝")
    async def process_re_register(message: types.Message, state: FSMContext):
        if db.get_event_state() != "registration":
            await message.answer(
                "Реєстрація завершена, дякуємо за інтерес! Спробуйте наступного року. 🚩",
                reply_markup=None
            )
            return
        await state.clear()
        await message.answer("♦️ Введи своє ім'я:")
        await state.set_state(Registration.name)

    @dp.message(lambda message: message.sticker or message.photo or message.video or message.animation)
    async def process_invalid_media_main(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if db.is_user_registered(user_id):
            name = db.get_user_data(user_id)
            await message.answer("‼️ Будь ласка, надсилай тільки текст або натискай на кнопки! Не стікери, фото, GIF чи відео.")
            await send_main_menu(message, state, db, registered=True, name=name)
        else:
            await message.answer("‼️ Будь ласка, надсилай тільки текст або натискай на кнопки! Не стікери, фото, GIF чи відео.")
            await send_main_menu(message, state, db)

    @dp.message(lambda message: message.text not in ["Інформація про CTF 🚩", "Хто такі BEST Lviv❓", "Моя команда 🫱🏻‍🫲🏿", "🚩 CTF завдання"])
    async def process_invalid_info_response(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("‼️ Будь ласка, натискай на кнопки! Не надсилай фото, гіфки, стікери чи голосові повідомлення.", reply_markup=get_main_menu_keyboard())
            return
        user_id = message.from_user.id
        if db.is_user_registered(user_id):
            name = db.get_user_data(user_id)
            await send_main_menu(message, state, db, registered=True, name=name)
        else:
            await send_main_menu(message, state, db)

    @dp.message(lambda message: message.text not in ["Інформація про CTF 🚩", "Хто такі BEST Lviv❓", "Моя команда 🫱🏻‍🫲🏿", "🚩 CTF завдання"] and db.is_user_registered(message.from_user.id))
    async def process_invalid_main_menu(message: types.Message, state: FSMContext):
        if not message.text:
            name = db.get_user_data(message.from_user.id)
            await message.answer("‼️ Будь ласка, натискай на кнопки! Не надсилай фото, гіфки, стікери чи голосові повідомлення.")
            await send_main_menu(message, state, db, registered=True, name=name)
            return
        name = db.get_user_data(message.from_user.id)
        await send_main_menu(message, state, db, registered=True, name=name)

    @dp.message(lambda message: message.text != "Зареєструватись у CTF-2025! 📝" and not db.is_user_registered(message.from_user.id))
    async def process_invalid_start(message: types.Message, state: FSMContext):
        if not message.text:
            await message.answer("‼️ Будь ласка, натискай на кнопки! Не надсилай фото, гіфки, стікери чи голосові повідомлення.")
        await send_main_menu(message, state, db)