import logging
from supabase import create_client
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from datetime import datetime
from zoneinfo import ZoneInfo
from matching import *
from dotenv import load_dotenv
import os
load_dotenv() 

# Timezone configuration
server_timezone = "Asia/Tashkent"
current_time = datetime.now(ZoneInfo(server_timezone))
print(current_time)


# Supabase configuration
url = "https://pghlbddjvcllgcqpvvxl.supabase.co"
key = os.getenv("SUPABASE_API_KEY")
supabase = create_client(url, key)

# Bot configuration
API_TOKEN = os.getenv("TELEGRAM_API_KEY")
bot_username = 'up2matesbot'
admin_id = "6193719398"
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Constants
COMMAND_START = 'start'
COMMAND_BAN = 'ban'
COMMAND_UNBAN = 'unban'
TEXT_MY_TOKENS = 'My Tokens'
TEXT_SEARCH_BUDDY = 'Search for Study Buddy'
TEXT_EDIT_PROFILE = 'Create/Edit Profile'
MSG_WELCOME = "Welcome! Please choose an option:"
MSG_NO_PROFILE = "📌 To help us find the perfect study buddy for you, please answer a few questions and create a profile. It won’t take long, but be honest and thoughtful with your responses – the matchmaking process will be based on your answers."
MSG_BANNED = "You are banned from using this bot."
MSG_TOKENS = "You have {tokens} tokens. Every day you are given 15 free tokens. One token is equal to one search at a time. If you want to get extra tokens, you can share your referral link to others. For each new user, you will be given five extra tokens."
MSG_NO_TOKENS = "You have no tokens. Please top up your tokens and try again."
MSG_NO_MATCH = "No suitable match found. Please try again later."
MSG_USER_INACTIVE = "Unfortunately, this user is no longer available for matchmaking."

# Define states for the finite state machine
class Form(StatesGroup):
    name = State()
    gender = State()
    age = State()
    location = State()
    interests = State()
    intro = State()
    contact = State()
    edit_choice = State()
    edit_age = State()
    edit_interests = State()
    edit_intro = State()
    edit_contact = State()
    prev_message_id = State()
    match_info = State()
    referrer_id = State()
    reported_user_id = State()
    broadcast_message = State()
    
main_router = Router()
profile_router = Router()
edit_router = Router()

dp.include_router(main_router)
dp.include_router(profile_router)
dp.include_router(edit_router)

# Helper function to fetch user data
async def fetch_user_data(user_id):
    data = supabase.table("telegram").select("*").eq("user_id", user_id).execute().data
    return data[0] if data else None

# Helper function to check if a user is banned
async def is_user_banned(user_id):
    try: 
        user = await fetch_user_data(user_id)
        return user['is_banned']
    except:
        return False

# Function to send a banned user message
async def handle_banned_user(message: types.Message):
    await message.answer(MSG_BANNED)

async def handle_banned_user_callback(callback: types.CallbackQuery):
    await callback.message.answer(MSG_BANNED)

# Function to format the user's profile for display
async def format_profile(user_data):
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

# Helper function to create reply markup
def create_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=TEXT_SEARCH_BUDDY),
                KeyboardButton(text=TEXT_EDIT_PROFILE),
                KeyboardButton(text=TEXT_MY_TOKENS)
            ]
        ],
        resize_keyboard=True,
    )

# Function to handle user profile creation/editing
async def process_profile_creation(state: FSMContext, user_data, user_id):
    data = await state.get_data()
    name = data.get('name')
    age = data.get('age')
    location = data.get('location')
    gender = data.get('gender') == 'Male'
    interests = data.get('interests')
    intro = data.get('intro')
    contact = data.get('contact')
    
    response = supabase.table("telegram").select("*", count="exact").execute()
    id = response.count + 1

    supabase.table("telegram").upsert({
        "id": id,
        "user_id": user_id,
        "name": name,
        "gender": gender,
        "age": int(age),
        "origin": location,
        "interests": interests,
        "bio": intro,
        "contact": contact,
        "is_active": 1,
        "referral_count": 0,
        "token": 20,
        "daily_referral": 0,
    }).execute()

    # Handle referrals and token management
    referrer_id = data.get("referrer_id")
    print(referrer_id)
    if referrer_id is not None:
        referrer_data = await fetch_user_data(referrer_id)
        if referrer_data:
            supabase.table("telegram").update({
                "referral_count": referrer_data["referral_count"] + 1,
                "token": referrer_data["token"] + 9
            }).eq("user_id", referrer_id).execute()

    await state.clear()
    await state.set_state(None)
    return "**Thank you! Your profile has been created/updated.**\n\nYou can now search for a study buddy:"

# Ignore old messages
bot_startup_time = current_time
async def ignore_old_messages(message: types.Message):
    if message.date < bot_startup_time:
        await message.answer("This message was sent while the bot was offline and cannot be processed.")
        return True
    return False

# character length checker
async def check_for_char_length(message: types.Message, text_to_check: str) -> bool:
    if len(text_to_check) < 100:
        await message.answer("Please write a bit more about yourself. Try again.")
        return True
    return False

# Main commands
@main_router.message(Command(COMMAND_START))
async def cmd_start(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    if await is_user_banned(message.from_user.id):  
        await handle_banned_user(message)
        return
        
    referrer_id = str(message.text[7:])
    await state.update_data(referrer_id=referrer_id)

    await message.answer(MSG_WELCOME, reply_markup=create_main_menu())

@main_router.message(F.text == 'Menu')
async def process_menu_button(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(MSG_WELCOME, reply_markup=create_main_menu())

@main_router.message(F.text == TEXT_MY_TOKENS)
async def get_tokens(message: types.Message):
    if await ignore_old_messages(message):
        return

    if await is_user_banned(message.from_user.id):
        await handle_banned_user(message)
        return

    user_data = await fetch_user_data(message.from_user.id)
    if user_data:
        timestamptz_str = user_data['last_search']
        last_datetime = datetime.fromisoformat(timestamptz_str)
        difference = datetime.now(ZoneInfo(server_timezone)) - last_datetime
        if difference.days > 0: 
            user_data['token'] += 15
        supabase.table("telegram").update({"last_search": datetime.now(ZoneInfo(server_timezone)).isoformat()}).eq("user_id", user_data["user_id"]).execute()
        supabase.table("telegram").update({"token": user_data["token"]}).eq("user_id", user_data["user_id"]).execute()

        await message.answer(MSG_TOKENS.format(tokens=user_data["token"]),
                             reply_markup=InlineKeyboardMarkup(
                                 inline_keyboard=[[InlineKeyboardButton(text="Copy Referral Link", callback_data="copy referral link")]]
                             ))

@main_router.callback_query(F.data == "copy referral link")
async def copy_referral_link(callback_query: types.CallbackQuery):
    referral_link = f"https://t.me/{bot_username}?start={callback_query.from_user.id}"
    await callback_query.message.answer(f"Here is your referral link:\n{referral_link}\n\nShare this link with others to refer them to the bot.")

@main_router.callback_query(lambda c: 'menu' in c.data)
async def menu(callback_query: types.CallbackQuery):
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return
    await callback_query.message.answer(MSG_WELCOME, reply_markup=create_main_menu())

@main_router.message(F.text == TEXT_SEARCH_BUDDY)
async def search_study_buddy(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    if await is_user_banned(message.from_user.id):
        await handle_banned_user(message)
        return

    user_data = await fetch_user_data(message.from_user.id)
    if not user_data:
        await state.set_state(Form.name)
        await message.answer(MSG_NO_PROFILE, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        await message.answer("📝<b>What is your name?</b>", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        return

    if user_data['token'] > 0:
        request = ' '.join(user_data["interests"])

        # Add 9 tokens daily
        timestamptz_str = user_data['last_search']
        if timestamptz_str is not None:
            last_datetime = datetime.fromisoformat(timestamptz_str)
        else:
            last_datetime = None
            await message.answer("No valid timestamp found for this user.")
            return
        
        difference = datetime.now(ZoneInfo(server_timezone)) - last_datetime
        if difference.days > 0: 
            user_data['token'] += 15

        found_user = await find_best_match(request, user_data)

        if found_user:
            await state.update_data(match_info=found_user)
            supabase.table("telegram").update({"token": user_data["token"] - 1}).eq("user_id", user_data['user_id']).execute()

            gender = "female" if not found_user["gender"] else "male"
            await message.answer(
                text=(
                    f"🤩 <b><i>Meet Your Future Study Mate!</i></b>🚀\n\n"
                    f"<b><i>👤Gender:</i></b> {gender}\n"
                    f"<b><i>📆Age:</i></b> {found_user['age']}\n"
                    f"<b><i>📍Location:</i></b> {found_user['origin']}\n"
                    f"<b><i>🏓Interests:</i></b> {', '.join(found_user['interests'])}\n\n"
                    f"<b><i>👋Brief Introduction (e.g.: test scores🧮, major achievements🏆, hobbies🏓, etc.):</i></b> {found_user['bio']}"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(text="Match 🎯", callback_data=f'match {found_user["user_id"]}'),
                            InlineKeyboardButton(text="Next ➡️", callback_data=f'next'),
                        ],
                        [
                            InlineKeyboardButton(text="Report", callback_data=f'report {found_user["user_id"]}'),
                            InlineKeyboardButton(text="Menu", callback_data='menu'),
                        ]
                    ]
                )
            )
        else:
            await message.answer(MSG_NO_MATCH)
    else:
        await message.answer(MSG_NO_TOKENS)

@main_router.callback_query(lambda c: 'menu' in c.data)
async def menu(callback_query: types.CallbackQuery):
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return
    await callback_query.message.answer(MSG_WELCOME, reply_markup=create_main_menu())

@main_router.callback_query(lambda c: 'match' in c.data)
async def match_profiles(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return
    
    match_user_id = callback_query.data.split()[1]

    await callback_query.message.answer("Your request for a study buddy has been sent. We will send contact information if that person accepts your request.")
    current_user_data = await fetch_user_data(callback_query.from_user.id)
    gender = "female" if not current_user_data["gender"] else "male"
    try:
        await bot.send_message(
            chat_id=match_user_id,
            text=(
                "Congratulations! Your profile was viewed by another user and they want to match with you. "
                "Here is some information about that person.\n"
                f"<b><i>👤Gender:</i></b> {gender}\n"
                f"<b><i>📆Age:</i></b> {current_user_data['age']}\n"
                f"<b><i>📍Location:</i></b> {current_user_data['origin']}\n\n"
                f"<b><i>🏓Interests:</i></b> {', '.join(current_user_data['interests'])}\n\n"
                f"<b><i>👋Brief Introduction (e.g.: test scores🧮, major achievements🏆, hobbies🏓, etc.):</i></b> {current_user_data['bio']}"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Accept ✅", callback_data=f'accept {current_user_data["user_id"]}'),
                        InlineKeyboardButton(text="Reject ❌", callback_data=f'reject {current_user_data["user_id"]}'),
                        InlineKeyboardButton(text="Report", callback_data=f'report {current_user_data["user_id"]}'),
                    ]
                ]
            )
        )
    except:
        await callback_query.message.answer(MSG_USER_INACTIVE)
        supabase.table("telegram").update({"is_active": False}).eq("user_id", match_user_id).execute()

@main_router.callback_query(lambda c: 'report' in c.data)
async def report_user(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return
    
    report_user_id = callback_query.data.split()[1]

    await callback_query.message.answer(
        "Please, give reasons why you want to report this user (offensive language in application, wrong contact information, or else).",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="offensive language", callback_data=f'offensive lang {report_user_id}'),
                ],
                [
                    InlineKeyboardButton(text="wrong contact info", callback_data=f'wrong contact info {report_user_id}'),
                ],
                [
                    InlineKeyboardButton(text="back", callback_data='back'),
                ]
            ]
        )
    )

@main_router.callback_query(lambda c: 'offensive lang' in c.data)
async def offensive_language_report(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return
    
    reported_user_id = callback_query.data.split()[2]
    reported_data = await fetch_user_data(reported_user_id)
    reporting_data = await fetch_user_data(callback_query.from_user.id)

    user_info = await bot.get_chat(reported_user_id)
    reported_username = user_info.username or "username not set"

    await callback_query.message.answer("Thank you for informing us! We will review the reported account and ban it if it violates our rules.")
    await bot.send_message(
        chat_id=admin_id,
        text=(
            f"Reporter: {reporting_data['name']} {reporting_data['contact']} {reporting_data['user_id']}\n"
            f"Reason for report: Offensive language\n"
            "Reported account:\n"
            f"<b><i>👤Name:</i></b> {reported_data['name']}\n"
            f"<b><i>🌟Gender:</i></b> {'female' if not reported_data['gender'] else 'male'}\n"
            f"<b><i>📆Age:</i></b> {reported_data['age']}\n"
            f"<b><i>📍Location:</i></b> {reported_data['origin']}\n\n"
            f"<b><i>🏓Interests:</i></b> {', '.join(reported_data['interests'])}\n\n"
            f"<b><i>👋Brief Introduction (e.g.: test scores🧮, major achievements🏆, hobbies🏓, etc.):</i></b> {reported_data['bio']}\n\n"
            f"<b><i>📝Contact:</i></b> @{reported_username} {reported_data['contact']}"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Ban", callback_data=f"ban {reported_data['id']}")],
                [InlineKeyboardButton(text="Disapprove", callback_data="disapprove")]
            ]
        )
    )

@main_router.callback_query(lambda c: 'wrong contact info' in c.data)
async def wrong_contact_info_report(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return

    reported_user_id = callback_query.data.split()[3]
    reported_data = await fetch_user_data(reported_user_id)
    reporting_data = await fetch_user_data(callback_query.from_user.id)

    await callback_query.message.answer("Thank you for reporting incorrect contact information. We will review the user's details.")

    await bot.send_message(
        chat_id=admin_id,
        text=(
            f"Reporter: {reporting_data['name']} {reporting_data['contact']} {reporting_data['user_id']}\n"
            f"Reason for report: Wrong Contact Info\n"
            "Reported account:\n"
            f"<b><i>👤Name:</i></b> {reported_data['name']}\n"
            f"<b><i>🌟Gender:</i></b> {'female' if not reported_data['gender'] else 'male'}\n"
            f"<b><i>📆Age:</i></b> {reported_data['age']}\n"
            f"<b><i>📍Location:</i></b> {reported_data['origin']}\n\n"
            f"<b><i>🏓Interests:</i></b> {', '.join(reported_data['interests'])}\n\n"
            f"<b><i>👋Brief Introduction (e.g.: test scores🧮, major achievements🏆, hobbies🏓, etc.):</i></b> {reported_data['bio']}\n\n"
            f"<b><i>📝Contact:</i></b> @{reported_user_id} {reported_data['contact']}"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Ban", callback_data=f"ban {reported_data['id']}")],
                [InlineKeyboardButton(text="Disapprove", callback_data="disapprove")]
            ]
        )
    )

@main_router.callback_query(lambda c: 'back' in c.data)
async def go_back(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return

    await callback_query.message.answer("Returning to the previous menu.", reply_markup=create_main_menu())

@main_router.callback_query(lambda c: 'ban' in c.data)
async def ban_user(callback_query: types.CallbackQuery):
    reported_id = callback_query.data.split()[1]
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer(f"The user number {reported_id} was permanently banned.")
    supabase.table("telegram").update({"is_banned": True}).eq("id", reported_id).execute()

@main_router.callback_query(lambda c: 'disapprove' in c.data)
async def ban_user(callback_query: types.CallbackQuery):
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer("The report for banning user was disapproved")

@main_router.callback_query(lambda c: 'next' in c.data)
async def next_studybuddy(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.delete()

    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return
    
    user_data = await fetch_user_data(callback_query.from_user.id)
    if not user_data or user_data['token'] <= 0:
        await callback_query.message.answer(MSG_NO_TOKENS)
        return

    request = ' '.join(user_data["interests"])

    # Add 9 tokens daily
    timestamptz_str = user_data['last_search']
    last_datetime = datetime.fromisoformat(timestamptz_str)
    difference = datetime.now(ZoneInfo(server_timezone)) - last_datetime
    if difference.days > 0: 
        user_data['token'] += 15

    found_user = await find_best_match(request, user_data)

    if found_user:
        await state.update_data(match_info=found_user)
        supabase.table("telegram").update({"token": user_data["token"] - 1}).eq("user_id", user_data['user_id']).execute()

        gender = "female" if not found_user["gender"] else "male"
        await callback_query.message.answer(
            text=(
                f"🤩 <b><i>Meet Your Future Study Mate!</i></b>🚀\n\n"
                f"<b><i>👤Gender:</i></b> {gender}\n"
                f"<b><i>📆Age:</i></b> {found_user['age']}\n"
                f"<b><i>📍Location:</i></b> {found_user['origin']}\n\n"
                f"<b><i>🏓Interests:</i></b> {', '.join(found_user['interests'])}\n\n"
                f"<b><i>👋Brief Introduction (e.g.: test scores🧮, major achievements🏆, hobbies🏓, etc.):</i></b> {found_user['bio']}"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Match 🎯", callback_data=f'match {found_user["user_id"]}'),
                        InlineKeyboardButton(text="Next ➡️", callback_data=f'next'),
                    ],
                    [
                        InlineKeyboardButton(text="Report", callback_data=f'report {found_user["user_id"]}'),
                        InlineKeyboardButton(text="Menu", callback_data='menu'),
                    ]
                ]
            )
        )
    else:
        await callback_query.message.answer(MSG_NO_MATCH)

@main_router.callback_query(lambda c: 'accept' in c.data)
async def accept(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return

    match_user_id = callback_query.data.split()[1]
    match_user_data = await fetch_user_data(match_user_id)
    current_user_data = await fetch_user_data(callback_query.from_user.id)

    if not match_user_data or not current_user_data:
        await callback_query.message.answer(MSG_USER_INACTIVE)
        return

    gender = "female" if not current_user_data["gender"] else "male"
    
    # Fetch user info using get_chat
    match_user_info = await bot.get_chat(match_user_id)
    current_user_info = await bot.get_chat(match_user_id)
    match_username = match_user_info.username or "Username not set"
    current_username = current_user_info.username or "Username not set"
    
    await bot.send_message(
        chat_id=match_user_id,
        text=(
            "Congratulations! Your profile was matched with an amazing person. "
            "Here is some information about that person.\n"
            f"<b><i>🗂Here is their profile:</i></b>\n\n"
            f"<b><i>👤Name:</i></b> {current_user_data['name']}\n"
            f"<b><i>🌟Gender:</i></b> {gender}\n"
            f"<b><i>📆Age:</i></b> {current_user_data['age']}\n"
            f"<b><i>📍Location:</i></b> {current_user_data['origin']}\n\n"
            f"<b><i>🏓Interests:</i></b> {', '.join(current_user_data['interests'])}\n\n"
            f"<b><i>👋Brief Introduction (e.g.: test scores🧮, major achievements🏆, hobbies🏓, etc.):</i></b> {current_user_data['bio']}\n\n"
            f"<b><i>📝Contact:</i></b> @{current_username} {current_user_data['contact']}"
        ),
        parse_mode="HTML",
    )
    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=(
            "Congratulations! Your profile was matched with an amazing person. "
            "Here is some information about that person.\n"
            f"<b><i>🗂Here is their profile:</i></b>\n\n"
            f"<b><i>👤Name:</i></b> {match_user_data['name']}\n"
            f"<b><i>🌟Gender:</i></b> {'female' if not match_user_data['gender'] else 'male'}\n"
            f"<b><i>📆Age:</i></b> {match_user_data['age']}\n"
            f"<b><i>📍Location:</i></b> {match_user_data['origin']}\n\n"
            f"<b><i>🏓Interests:</i></b> {', '.join(match_user_data['interests'])}\n\n"
            f"<b><i>👋Brief Introduction (e.g.: test scores🧮, major achievements🏆, hobbies🏓, etc.):</i></b> {match_user_data['bio']}\n\n"
            f"<b><i>📝Contact:</i></b> @{match_username} {match_user_data['contact']}"
        ),
        parse_mode="HTML",
    )

@main_router.callback_query(lambda c: 'reject' in c.data)
async def reject(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return

    match_user_id = callback_query.data.split()[1]
    match_user_data = await fetch_user_data(match_user_id)
    current_user_data = await fetch_user_data(callback_query.from_user.id)

    if not match_user_data or not current_user_data:
        await callback_query.message.answer(MSG_USER_INACTIVE)
        return

    gender = "female" if not current_user_data["gender"] else "male"
    
    match_user_info = await bot.get_chat(match_user_id)
    current_user_info = await bot.get_chat(match_user_id)
    match_username = match_user_info.username or "Username not set"
    current_username = current_user_info.username or "Username not set"
    
    await bot.send_message(
        chat_id=match_user_id,
        text=(
            f"Unfortunately, your request for matching was declined 😔. \n\n"
            "People come and go. It really doesn't matter; what really matters is how you learn from the experience. And remember, blocking the bot doesn't help.\n\n"
            "<b>Fortunately, you still can find the right person using our bot 🥳.</b>\n\n"
            "PS: To get more matches, you can improve your profile."
        ),
        parse_mode="HTML",
    )
    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text="<b>We appreciate your desicion.</b>",
        parse_mode="HTML",
    )

@main_router.message(F.text == TEXT_EDIT_PROFILE)
async def create_edit_profile(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    if await is_user_banned(message.from_user.id):
        await handle_banned_user(message)
        return

    user_data = await fetch_user_data(message.from_user.id)
    if not user_data:
        await state.set_state(Form.name)
        await message.answer(MSG_NO_PROFILE, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        await message.answer("📝<b>What is your name?</b>", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        return

    profile_text = await format_profile(user_data)
    msg = await message.answer(profile_text, reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Edit", callback_data="edit")],
            [InlineKeyboardButton(text="Save and Return", callback_data="save")]
        ]
    ), parse_mode="HTML")
    await state.update_data(prev_message_id=msg.message_id)

@edit_router.callback_query(F.data == "save")
async def save_profile(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_message_id = data.get('prev_message_id')
    if prev_message_id:
        await callback_query.message.bot.delete_message(callback_query.message.chat.id, prev_message_id)
        
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return
    
    await callback_query.message.answer("Your profile has been saved.")
    await cmd_start(callback_query.message, state)

@edit_router.callback_query(F.data == "edit")
async def edit_profile(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prev_message_id = data.get('prev_message_id')
    if prev_message_id:
        await callback_query.message.bot.delete_message(callback_query.message.chat.id, prev_message_id)
    await state.set_state(Form.edit_choice)
    await callback_query.message.answer(
        "What would you like to edit?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Age", callback_data="edit_age")],
                [InlineKeyboardButton(text="Interests", callback_data="edit_interests")],
                [InlineKeyboardButton(text="Intro", callback_data="edit_intro")],
                [InlineKeyboardButton(text="Contact", callback_data="edit_contact")]
            ]
        )
    )
    await callback_query.answer()

@edit_router.callback_query(F.data.in_({"edit_age", "edit_interests", "edit_intro", "edit_contact"}))
async def process_edit_callback(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "edit_age":
        await state.set_state(Form.edit_age)
        await callback_query.message.answer("<b>📅 Please enter your new age:</b>", parse_mode='HTML')
    elif callback_query.data == "edit_interests":
        await state.set_state(Form.edit_interests)
        await callback_query.message.answer("<b>📋 Please list five to ten interests, separated by commas:</b>", parse_mode='HTML')
    elif callback_query.data == "edit_intro":
        await state.set_state(Form.edit_intro)
        await callback_query.message.answer("<b>💬 Please enter your new introduction:</b>", parse_mode='HTML')
    elif callback_query.data == "edit_contact":
        await state.set_state(Form.edit_contact)
        await callback_query.message.answer("<b>📬 Please enter your contact information (e.g., email, phone number):</b>", parse_mode='HTML')
    await callback_query.answer()

@edit_router.message(Form.edit_age)
async def process_edit_age(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    age = message.text
    if not age.isdigit():
        await message.answer("⚠️ <b>Please enter a valid number for your age.</b>", parse_mode='HTML')
        return
    await state.update_data(age=age)
    user_id = message.from_user.id
    supabase.table("telegram").update({"age": age}).eq("user_id", user_id).execute()

    await message.answer("✅ <b>Your age has been updated.</b>", parse_mode='HTML')
    await create_edit_profile(message, state)

@edit_router.message(Form.edit_interests)
async def process_edit_interests(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    interests_text = message.text
    interests = [interest.strip() for interest in interests_text.split(',') if interest.strip()]
    if len(interests) < 5 or len(interests) > 10:
        await message.answer("📋 <b>Please list five to ten interests, separated by commas.</b>", parse_mode='HTML')
        return
    await state.update_data(interests=interests)

    user_id = message.from_user.id
    supabase.table("telegram").update({"interests": interests}).eq("user_id", user_id).execute()

    await message.answer("✅ <b>Your interests have been updated.</b>", parse_mode='HTML')
    await create_edit_profile(message, state)

@edit_router.message(Form.edit_intro)
async def process_edit_intro(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    intro = message.text
    if await check_for_char_length(message, intro):
        return
    await state.update_data(intro=intro)

    user_id = message.from_user.id
    supabase.table("telegram").update({"bio": intro}).eq("user_id", user_id).execute()

    await message.answer("✅ <b>Your introduction has been updated.</b>", parse_mode='HTML')
    await create_edit_profile(message, state)

@edit_router.message(Form.edit_contact)
async def process_edit_contact(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    contact_info = f"(telegram username: @{message.from_user.username}) {message.text}"
    await state.update_data(contact=contact_info)

    user_id = message.from_user.id
    supabase.table("telegram").update({"contact": contact_info}).eq("user_id", user_id).execute()

    await message.answer("✅ <b>Your contact information has been updated.</b>", parse_mode='HTML')
    await create_edit_profile(message, state)

@profile_router.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    logging.info("Processing name")
    await state.update_data(name=message.text)
    await state.set_state(Form.gender)
    await message.answer(
        "<b>🔎 What is your gender?</b>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Male"), KeyboardButton(text="Female")]
            ],
            resize_keyboard=True,
        ),
        parse_mode='HTML'
    )

@profile_router.message(Form.gender)
async def process_gender(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    logging.info("Processing gender")
    if message.text not in ['Male', 'Female']:
        await message.answer("⚠️ <b>Please choose a valid gender option: Male or Female.</b>", parse_mode='HTML')
        return
    await state.update_data(gender=message.text)
    await state.set_state(Form.age)
    await message.answer(
        "<b>🔎 How old are you?</b>\n<i>Important: enter a valid number for your age.</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@profile_router.message(Form.age)
async def process_age(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    logging.info("Processing age")
    if not message.text.isdigit():
        await message.answer("⚠️ <b>Please enter a valid number for your age.</b>", parse_mode='HTML')
        return
    await state.update_data(age=message.text)
    await state.set_state(Form.location)
    await message.answer("<b>🔎 Where are you from?</b>", parse_mode='HTML')

@profile_router.message(Form.location)
async def process_location(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    logging.info("Processing location")
    await state.update_data(location=message.text)
    await state.set_state(Form.interests)
    await message.answer(
        "<b>🔎 List five to ten activities, hobbies, or interests of yours.</b>\n<i>Important: separate them by commas.</i>",
        parse_mode='HTML'
    )

@profile_router.message(Form.interests)
async def process_interests(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    logging.info("Processing interests")
    
    interests_text = message.text
    interests = [interest.strip() for interest in interests_text.split(',') if interest.strip()]
    if len(interests) < 5 or len(interests) > 10:
        await message.answer("⚠️ <i>Please, list five to ten interests, separated by commas.</i>", parse_mode='HTML')
        return
    await state.update_data(interests=interests)
    await state.set_state(Form.intro)
    await message.answer(
        "<b>🔎 Write briefly about yourself, it will be placed as your introduction to other users.</b>\n<i>Include any additional information you'd like to share (e.g., test scores, major achievements).</i>",
        parse_mode='HTML'
    )

@profile_router.message(Form.intro)
async def process_intro(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    logging.info("Processing intro")
    
    intro = message.text
    if await check_for_char_length(message, intro):
        return
    await state.update_data(intro=intro)
    await state.set_state(Form.contact)
    await message.answer(
        "<b>🔎 Provide your contact information (e.g., Telegram username, Instagram, etc.)</b>\n<i>Important: The contact information will be used for contacting each other and will be shared only after both sides have agreed to match.</i>",
        parse_mode='HTML'
    )

@profile_router.message(Form.contact)
async def process_contact(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    logging.info("Processing contact")
    contact_info = f"(telegram username: @{message.from_user.username}) {message.text}"
    await state.update_data(contact=contact_info)

    user_data = await fetch_user_data(message.from_user.id) or {}
    response_message = await process_profile_creation(state, user_data, message.from_user.id)

    await message.answer(
        response_message,
        reply_markup=create_main_menu(),
        parse_mode='Markdown'
    )

@main_router.message(Command("send_all"))
async def send_all_command(message: types.Message):
    if message.from_user.id == int(admin_id):
        broadcast_content = message.text[len("/send_all "):].strip()

        if not broadcast_content:
            await message.answer("Please provide a message to broadcast after the /send_all command.")
            return
        
        users = supabase.table("telegram").select("user_id").eq("is_active", True).execute().data
        for user_id in users:
            try:
                await message.bot.send_message(chat_id=user_id["user_id"], text=broadcast_content)
            except Exception as e:
                print(f"Failed to send message to {user_id}: {e}")

        await message.answer("The message has been broadcast to all users.")
    else:
        await message.answer("You are not authorized to use this command.")

if __name__ == '__main__':
    import asyncio
    asyncio.run(dp.start_polling(bot))
