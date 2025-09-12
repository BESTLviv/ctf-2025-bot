import os
import sys
from dotenv import load_dotenv

# Завантаження .env файлу з явним шляхом на початку
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
print("BOT_TOKEN:", os.getenv("BOT_TOKEN"))  # Дебаг вивід для перевірки
print("MONGODB_URI:", os.getenv("MONGODB_URI"))  # Дебаг вивід для перевірки

# Тепер імпорти, які залежать від env
import config

# Решта імпортів
import psutil
import asyncio
import logging
from aiogram import Bot, Dispatcher
from admin.admin_handlers import register_admin_handlers
from handlers.user_handlers import register_user_handlers
from handlers.info_ctf_handlers import register_info_ctf_handlers
from handlers.info_best_handlers import register_info_best_handlers
from handlers.team_handlers import register_team_handlers
from handlers.cv_handlers import register_cv_handlers
from database import Database

# Дебаг: виведення sys.path
print("sys.path:", sys.path)

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_bot_running():
    for proc in psutil.process_iter(['name', 'cmdline']):
        if 'python' in proc.info['name'] and 'main.py' in ' '.join(proc.info['cmdline']):
            return True
    return False

async def main():
    # Перевірка, чи всі необхідні змінні середовища присутні
    required_vars = ["BOT_TOKEN", "MONGODB_URI"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
        return

    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set or is None")
        print("Error: BOT_TOKEN is not set or is None")
        return

    if is_bot_running():
        logger.error("Another instance of the bot is already running!")
        print("Error: Another instance of the bot is already running!")
        return

    # Ініціалізація бота та диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Ініціалізація бази даних
    try:
        db = Database(config.MONGODB_URI)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        print(f"Error: Failed to initialize database: {e}")
        return

    # Реєстрація обробників
    print("Registering handlers...")
    try:
        register_admin_handlers(dp, db, bot)
        print("Admin handlers registered")
        register_user_handlers(dp, db, bot)
        print("User handlers registered")
        register_info_ctf_handlers(dp, db, bot)
        print("Info CTF handlers registered")
        register_info_best_handlers(dp, db, bot)
        print("Info BEST handlers registered")
        register_team_handlers(dp, db, bot)
        print("Team handlers registered")
        register_cv_handlers(dp, db, bot)
        print("CV handlers registered")
    except Exception as e:
        logger.error(f"Error registering handlers: {e}")
        print(f"Error registering handlers: {e}")
        raise

    # Запуск бота
    try:
        logger.info("Starting bot polling")
        print("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        print(f"Error running bot: {e}")
    finally:
        await bot.session.close()
        logger.info("Bot stopped")
        print("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())