import logging
import os
from aiogram import Dispatcher, types
from aiogram.types import FSInputFile
import config

logger = logging.getLogger(__name__)

def get_back_to_main_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="Повернутися до головного меню")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def register_info_ctf_handlers(dp: Dispatcher, db=None, bot=None):
    @dp.message(lambda message: message.text == "Інформація про CTF 🚩")
    async def process_info_ctf(message: types.Message):
        image_path = os.path.join(config.ASSETS_PATH, "ctf.png")
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at {image_path}")
            await message.answer("‼️ Виникла помилка: зображення ctf.png не знайдено. Але не хвилюйся, продовжимо!")
        else:
            try:
                photo = FSInputFile(path=image_path)
                await message.answer_photo(photo=photo, caption="Інформація про CTF 🚩")
            except Exception as e:
                logger.error(f"Failed to send ctf.png: {str(e)}")
                await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")
        
        await message.answer(
            "<b>BEST CTF — це командні змагання з кібербезпеки, в яких учасники виконують завдання з різних категорій.</b>\n"
            "За виконання завдань вам розкриваються прапорці 🚩, за які ви отримуєте бали. 🏅\n"
            "👉 Стиль змагань — <b>Jeopardy</b>:\n"
            "📌 Категорії:\n\n"
            "  <b>🔐 Cryptography</b>\n"
            "  <b>🔄 Reverse</b>\n"
            "  <b>💥 PWN</b>\n"
            "  <b>🕵️‍♂️ Forensic</b>\n"
            "  <b>🌐 OSINT</b>\n"
            "  <b>🧩 MISC</b>\n\n"
            "А наприкінці усі зможуть позмагатись у додаткових номінаціях, а саме: \n"
            "<b>King of the Hill 👑</b> або <b>Write-Up competition 📝</b>\n\n"
            "<b>Дата проведення: 22 листопада 2025 🚩</b>\n"
            "Тому позначай цей день у календарі, щоб не пропустити 🗓 \nДо зустрічі, чемпіоне! 😄",
            parse_mode="HTML",
            reply_markup=get_back_to_main_menu_keyboard()
        )