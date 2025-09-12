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

def register_info_best_handlers(dp: Dispatcher, db=None, bot=None):
    @dp.message(lambda message: message.text == "Хто такі BEST Lviv❓")
    async def process_info_best(message: types.Message):
        image_path = os.path.join(config.ASSETS_PATH, "best.png")
        if not os.path.exists(image_path):
            logger.error(f"Image file not found at {image_path}")
            await message.answer("‼️ Виникла помилка: зображення best.png не знайдено. Але не хвилюйся, продовжимо!")
        else:
            try:
                photo = FSInputFile(path=image_path)
                await message.answer_photo(photo=photo, caption="Хто такі BEST Lviv ❓")
            except Exception as e:
                logger.error(f"Failed to send best.png: {str(e)}")
                await message.answer(f"‼️ Виникла помилка при відправці зображення: {str(e)}. Але не хвилюйся, продовжимо!")
        
        await message.answer(
            "<b>BEST Lviv</b> — це осередок міжнародної <b>неприбуткової, непартійної, молодіжної організації</b>.\n"
            "Створено у <b>2002</b> році при <b>Національному університеті \"Львівська політехніка\"</b>.\n\n"
            "Наша діяльність: <b>налагодження зв’язків між cтудентами, компаніями та університетом</b>.\n"
            "Ми — один із трьох LBG в Україні (<b>Київ, Львів, Вінниця</b>).\n\n"
            "🎯 <b>Місія</b>: розвиток студентів.\n"
            "🌍 <b>Візія</b>: сила у різноманітті.\n\n"
            "Щороку ми організовуємо близько <b>5 масштабних івентів</b>, серед яких:\n\n"
            "  <b>🚩 CTF</b> (Capture the Flag)\n"
            "  <b>👾 HACKath0n</b>\n"
            "  <b>🚀 BEC</b> (Best Engineering Competition)\n"
            "  <b>🎓 BTW</b> (BEST Training Week)\n"
            "  <b>💼 ІЯК</b> (Інженерний Ярмарок Кар’єри)",
            parse_mode="HTML",
            reply_markup=get_back_to_main_menu_keyboard()
        )