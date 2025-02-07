# bot.py
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import API_TOKEN
from routers import main_router, profile_router, edit_router  # Import your routers

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Include routers
dp.include_router(main_router.router)
dp.include_router(profile_router.router)
dp.include_router(edit_router.router)
# (If you create teacher_router.py, include it as well.)

__all__ = ["bot", "dp"]
