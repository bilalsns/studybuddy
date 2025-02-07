# routers/main_router.py
from aiogram import Router, types
from aiogram.filters import Command, Text
from config import MSG_WELCOME, TEXT_MY_TOKENS, TEXT_SEARCH_BUDDY, TEXT_LOOKING_FOR_TEACHERS, TEXT_BECOME_TEACHER
from utils import create_main_menu, ignore_old_messages
from db import fetch_user_data
from models import Form

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state):
    if await ignore_old_messages(message):
        return
    # (You can add banned-user check and referral logic here)
    await message.answer(MSG_WELCOME, reply_markup=create_main_menu())

@router.message(Text(text="Menu"))
async def process_menu_button(message: types.Message, state):
    await state.clear()
    await message.answer(MSG_WELCOME, reply_markup=create_main_menu())

# Add additional handlers such as:
# - Getting tokens (TEXT_MY_TOKENS)
# - Searching for study buddy (TEXT_SEARCH_BUDDY)
# - Handling reports and matching
# … etc.
