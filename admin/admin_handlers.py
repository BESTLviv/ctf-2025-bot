import logging
from aiogram import Dispatcher, types
from aiogram.fsm.context import FSMContext
from states.admin import AdminState
from database import Database
import config

logger = logging.getLogger(__name__)

def get_admin_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Розсилка 📢")],
            [types.KeyboardButton(text="Вихід з адмінпанелі 🚪")]
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

    @dp.message(lambda message: message.text in ["Розсилка 📢", "Вихід з адмінпанелі 🚪"], AdminState.main)
    async def process_admin_menu(message: types.Message, state: FSMContext):
        if message.text == "Розсилка 📢":
            await message.answer("Введіть текст для розсилки:")
            await state.set_state(AdminState.broadcast)
        elif message.text == "Вихід з адмінпанелі 🚪":
            await message.answer("Ви вийшли з адмінпанелі.")
            await state.clear()

    @dp.message(AdminState.main)
    async def process_invalid_admin_menu(message: types.Message, state: FSMContext):
        await message.answer("Вітаю, ви в адмінпанелі!\n‼️ Будь ласка, вибери один із варіантів нижче!", reply_markup=get_admin_menu_keyboard())

    @dp.message(AdminState.broadcast)
    async def process_broadcast_text(message: types.Message, state: FSMContext):
        broadcast_text = message.text
        try:
            participants = db.get_participants()
            for participant in participants:
                if "chat_id" in participant:
                    try:
                        await bot.send_message(
                            chat_id=participant["chat_id"],
                            text=broadcast_text,
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.error(f"Error sending broadcast to user {participant['user_id']}: {e}")
            await message.answer("Розсилка завершена.")
        except Exception as e:
            logger.error(f"Error during broadcast: {e}")
            await message.answer("Виникла помилка під час розсилки.")
        await message.answer("Вітаю, ви в адмінпанелі!", reply_markup=get_admin_menu_keyboard())
        await state.set_state(AdminState.main)