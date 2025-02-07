# config.py
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot
from aiogram.fsm.storage.memory import MemoryStorage

# Logging and timezone
logging.basicConfig(level=logging.INFO)
SERVER_TIMEZONE = "Asia/Tashkent"
BOT_STARTUP_TIME = datetime.now(ZoneInfo(SERVER_TIMEZONE))

# Supabase configuration
SUPABASE_URL = "https://pghlbddjvcllgcqpvvxl.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"

# Bot configuration
API_TOKEN = "7495888476:AAGymgKPkmjYXISWNGBMtsx1XD3JC8KP7XA"
BOT_USERNAME = 'up2matesbot'
ADMIN_ID = "6193719398"

# Constants for messages, commands, button texts, etc.
COMMAND_START = 'start'
COMMAND_BAN = 'ban'
COMMAND_UNBAN = 'unban'
TEXT_MY_TOKENS = 'My Tokens'
TEXT_SEARCH_BUDDY = 'Search for Study Buddy'
TEXT_EDIT_PROFILE = 'Create/Edit Profile'
MSG_WELCOME = "Welcome! Please choose an option:"
MSG_NO_PROFILE = "📌 To help us find the perfect study buddy for you, please answer a few questions and create a profile. It won’t take long, but be honest and thoughtful with your responses – the matchmaking process will be based on your answers."
MSG_BANNED = "You are banned from using this bot."
# … etc.
