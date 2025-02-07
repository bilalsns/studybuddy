# utils.py
from datetime import datetime
from zoneinfo import ZoneInfo
from config import SERVER_TIMEZONE, BOT_STARTUP_TIME
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def create_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Search for Study Buddy"),
                KeyboardButton(text="Create/Edit Profile"),
                KeyboardButton(text="My Tokens")
            ],
            [
                KeyboardButton(text="Looking for Teachers"),
                KeyboardButton(text="Become a Teacher")
            ]
        ],
        resize_keyboard=True,
    )

async def ignore_old_messages(message) -> bool:
    if message.date < BOT_STARTUP_TIME:
        await message.answer("This message was sent while the bot was offline and cannot be processed.")
        return True
    return False

async def check_for_bad_words(message, text_to_check: str) -> bool:
    # Replace the following with your actual dirty words checking logic:
    if "badword" in text_to_check.lower():
        await message.answer("Please avoid using inappropriate language. Try again.")
        return True
    return False

async def check_for_char_length(message, text_to_check: str) -> bool:
    if len(text_to_check) < 100:
        await message.answer("Please write a bit more about yourself. Try again.")
        return True
    return False

def format_profile(user_data) -> str:
    gender = "female" if not user_data["gender"] else "male"
    return (
        f"👤<b>Your Profile</b>\n\n"
        f"✏️<b>Name:</b> {user_data['name']}\n"
        f"👥<b>Gender:</b> {gender}\n"
        f"📆<b>Age:</b> {user_data['age']}\n"
        f"📍<b>Location:</b> {user_data['origin']}\n"
        f"🏓<b>Interests:</b> {', '.join(user_data['interests'])}\n"
        f"📝<b>Intro:</b> {user_data['bio']}\n"
        f"📨<b>Contact:</b> {user_data['contact']}\n"
    )

# You can also add your matchmaking functions here
