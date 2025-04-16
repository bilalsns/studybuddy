import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types, F, Router, executor
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv
from supabase import create_client

# Import qilish: matching funksiyalari va interests uchun categories
from matching import *
from interests_keyboard import categories

load_dotenv()

########################
# LANGUAGE MODULE CODE #
########################

# Tarjimalar lug'ati va ishlatiladigan matnlar
translations = {
    "uz": {
        "language_name": "O'zbekcha",
        "choose_language": "Tilni tanlang / Выберите язык / Select language:",
        "press_buttons": "Iltimos, tilni tanlash tugmalaridan birini bosing.",
        "switch_message": "Tilni o'zgartirish uchun, iltimos, quyidagi tugmalardan birini bosing:",
        "show_data_message": "Ma'lumotlarni ko'rsatish uchun /data buyrug'ini yuboring.",
        "chosen_lang_message": "Tanlangan til: "
    },
    "ru": {
        "language_name": "Русский",
        "choose_language": "Tilni tanlang / Выберите язык / Select language:",
        "press_buttons": "Пожалуйста, нажмите одну из кнопок ниже для выбора языка.",
        "switch_message": "Чтобы изменить язык, пожалуйста, нажмите одну из кнопок ниже:",
        "show_data_message": "Чтобы показать данные, введите команду /data.",
        "chosen_lang_message": "Выбранный язык: "
    },
    "en": {
        "language_name": "English",
        "choose_language": "Tilni tanlang / Выберите язык / Select language:",
        "press_buttons": "Please press one of the buttons below to choose a language.",
        "switch_message": "To switch the language, please press one of the buttons below:",
        "show_data_message": "Use /data to display the categories.",
        "chosen_lang_message": "Chosen language: "
    }
}

# Har bir foydalanuvchining tilini xotirada saqlash
user_language = {}

def language_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    uz_button = types.InlineKeyboardButton(
        text=translations["uz"]["language_name"],
        callback_data="lang_uz"
    )
    ru_button = types.InlineKeyboardButton(
        text=translations["ru"]["language_name"],
        callback_data="lang_ru"
    )
    en_button = types.InlineKeyboardButton(
        text=translations["en"]["language_name"],
        callback_data="lang_en"
    )
    keyboard.add(uz_button, ru_button, en_button)
    return keyboard

# Til bilan bog'liq komandalar uchun alohida router
lang_router = Router()

@lang_router.message_handler(commands=['language'])
async def select_language(message: types.Message):
    if message.from_user.id not in user_language:
        user_language[message.from_user.id] = "uz"
    lang_code = user_language[message.from_user.id]
    tr = translations[lang_code]
    welcome_text = f"{tr['choose_language']}\n{tr['press_buttons']}"
    await message.answer(welcome_text, reply_markup=language_keyboard())

@lang_router.callback_query_handler(lambda c: c.data and c.data.startswith('lang_'))
async def process_language(callback_query: types.CallbackQuery):
    lang_code = callback_query.data.split('_')[1]  # 'uz', 'ru', yoki 'en'
    user_language[callback_query.from_user.id] = lang_code
    tr = translations[lang_code]
    confirmation_text = tr["chosen_lang_message"] + tr["language_name"]
    await callback_query.answer(confirmation_text)
    await callback_query.message.answer("Language updated. Use /start to view the main menu.")

@lang_router.message_handler(commands=['switch'])
async def switch_language(message: types.Message):
    lang_code = user_language.get(message.from_user.id, "uz")
    tr = translations[lang_code]
    await message.answer(tr["switch_message"], reply_markup=language_keyboard())

@lang_router.message_handler(commands=['data'])
async def send_data(message: types.Message):
    lang_code = user_language.get(message.from_user.id, "uz")
    tr = translations[lang_code]
    # Misol uchun barcha til nomlarini ro'yxat shaklida yuboramiz
    text = "\n".join([f"- {translations[code]['language_name']}" for code in translations])
    await message.answer(text)

###########################
# END OF LANGUAGE MODULE  #
###########################

# TIMEZONE CONFIGURATION
server_timezone = "Asia/Tashkent"
current_time = datetime.now(ZoneInfo(server_timezone))
print(current_time)

# SUPABASE CONFIGURATION
url = "https://pghlbddjvcllgcqpvvxl.supabase.co"
key = os.getenv("SUPABASE_API_KEY")
supabase = create_client(url, key)

# BOT CONFIGURATION
bot_username = '@chilldlabourbot'
admin_id = "6193719398"
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_API_KEY")
bot = Bot(token=TOKEN)
storage = MemoryStorage()

# Dispatcher va Routerlar
dp = Dispatcher(storage=storage)
dp.include_router(lang_router)  # Til komandalari shu yerda
main_router = Router()
profile_router = Router()
edit_router = Router()
dp.include_router(main_router)
dp.include_router(profile_router)
dp.include_router(edit_router)

# CONSTANTS (Matnlar va komandalar)
COMMAND_START = 'start'
COMMAND_BAN = 'ban'
COMMAND_UNBAN = 'unban'
TEXT_MY_TOKENS = 'My Tokens'
TEXT_SEARCH_BUDDY = 'Search for Study Buddy'
TEXT_EDIT_PROFILE = 'Create/Edit Profile'
MSG_WELCOME = "Welcome! Please choose an option:"
MSG_NO_PROFILE = ("📌 To help us find the perfect study buddy for you, please answer a few questions and create a profile. "
                  "It won’t take long, but be honest and thoughtful with your responses – the matchmaking process will be based on your answers.")
MSG_BANNED = "You are banned from using this bot."
MSG_TOKENS = ("You have {tokens} tokens. Every day you are given 15 free tokens. One token equals one search. "
              "If you want extra tokens, share your referral link. For each new user, you get five extra tokens.")
MSG_NO_TOKENS = "You have no tokens. Please top up your tokens and try again."
MSG_NO_MATCH = "No suitable match found. Please try again later."
MSG_USER_INACTIVE = "Unfortunately, this user is no longer available for matchmaking."

# Finite State Machine (FSM) States
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

#######################
# HELPER FUNCTIONS
#######################

def get_all_exams(exam_list):
    all_exams = []
    for item in exam_list:
        if isinstance(item, list):
            for sub_item in item[1:]:
                if isinstance(sub_item, list):
                    all_exams.append(sub_item[0])
                else:
                    all_exams.append(sub_item)
        else:
            all_exams.append(item)
    return all_exams

async def fetch_user_data(user_id):
    data = supabase.table("telegram").select("*").eq("user_id", user_id).execute().data
    return data[0] if data else None

async def is_user_banned(user_id):
    try: 
        user = await fetch_user_data(user_id)
        return user['is_banned']
    except Exception:
        return False

async def handle_banned_user(message: types.Message):
    await message.answer(MSG_BANNED)

async def handle_banned_user_callback(callback: types.CallbackQuery):
    await callback.message.answer(MSG_BANNED)

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
    new_id = response.count + 1

    supabase.table("telegram").upsert({
        "id": new_id,
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

    referrer_id = data.get("referrer_id")
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

async def ignore_old_messages(message: types.Message):
    if message.date < current_time:
        await message.answer("This message was sent while the bot was offline and cannot be processed.")
        return True
    return False

async def check_for_char_length(message: types.Message, text_to_check: str) -> bool:
    if len(text_to_check) < 100:
        await message.answer("Please write a bit more about yourself. Try again.")
        return True
    return False

#######################
# MAIN ROUTERS & HANDLERS
#######################

@main_router.message(Command(COMMAND_START))
async def cmd_start(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    if await is_user_banned(message.from_user.id):  
        await handle_banned_user(message)
        return
        
    referrer_id = str(message.text[7:]) if len(message.text) > 7 else None
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

        await message.answer(
            MSG_TOKENS.format(tokens=user_data["token"]),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Copy Referral Link", callback_data="copy referral link")]]
            )
        )
    else:
        await message.answer(MSG_NO_TOKENS)

@main_router.callback_query_handler(F.data == "copy referral link")
async def copy_referral_link(callback_query: types.CallbackQuery):
    referral_link = f"https://t.me/{bot_username}?start={callback_query.from_user.id}"
    await callback_query.message.answer(f"Here is your referral link:\n{referral_link}\n\nShare this link to refer others.")

@main_router.callback_query_handler(lambda c: 'menu' in c.data)
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
        timestamptz_str = user_data['last_search']
        if timestamptz_str is not None:
            last_datetime = datetime.fromisoformat(timestamptz_str)
        else:
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
                    f"<b><i>📍Location:</i></b> {found_user['origin']}\n\n"
                    f"<b><i>🏓Interests:</i></b> {', '.join(found_user['interests'])}\n\n"
                    f"<b><i>👋Brief Intro:</i></b> {found_user['bio']}"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(text="Match 🎯", callback_data=f'match {found_user["user_id"]}'),
                            InlineKeyboardButton(text="Next ➡️", callback_data=f'next')
                        ],
                        [
                            InlineKeyboardButton(text="Report", callback_data=f'report {found_user["user_id"]}'),
                            InlineKeyboardButton(text="Menu", callback_data='menu')
                        ]
                    ]
                )
            )
        else:
            await message.answer(MSG_NO_MATCH)
    else:
        await message.answer(MSG_NO_TOKENS)

@main_router.callback_query_handler(lambda c: 'match' in c.data)
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
                f"Congratulations! Your profile was viewed and the user wants to match with you.\n"
                f"<b><i>👤Gender:</i></b> {gender}\n"
                f"<b><i>📆Age:</i></b> {current_user_data['age']}\n"
                f"<b><i>📍Location:</i></b> {current_user_data['origin']}\n\n"
                f"<b><i>🏓Interests:</i></b> {', '.join(current_user_data['interests'])}\n\n"
                f"<b><i>👋Brief Intro:</i></b> {current_user_data['bio']}"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="Accept ✅", callback_data=f'accept {current_user_data["user_id"]}'),
                    InlineKeyboardButton(text="Reject ❌", callback_data=f'reject {current_user_data["user_id"]}'),
                    InlineKeyboardButton(text="Report", callback_data=f'report {current_user_data["user_id"]}')
                ]]
            )
        )
    except Exception:
        await callback_query.message.answer(MSG_USER_INACTIVE)
        supabase.table("telegram").update({"is_active": False}).eq("user_id", match_user_id).execute()

@main_router.callback_query_handler(lambda c: 'report' in c.data)
async def report_user(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return
    
    report_user_id = callback_query.data.split()[1]
    await callback_query.message.answer(
        "Please, give reasons for reporting this user (offensive language, wrong contact info, etc.).",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="offensive language", callback_data=f'offensive lang {report_user_id}')],
                [InlineKeyboardButton(text="wrong contact info", callback_data=f'wrong contact info {report_user_id}')],
                [InlineKeyboardButton(text="back", callback_data='back')]
            ]
        )
    )

@main_router.callback_query_handler(lambda c: 'offensive lang' in c.data)
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
    await callback_query.message.answer("Thank you for reporting. We will review this account.")
    await bot.send_message(
        chat_id=admin_id,
        text=(
            f"Reporter: {reporting_data['name']} {reporting_data['contact']} {reporting_data['user_id']}\n"
            f"Reason: Offensive language\n"
            f"Reported:\n"
            f"<b><i>👤Name:</i></b> {reported_data['name']}\n"
            f"<b><i>🌟Gender:</i></b> {'female' if not reported_data['gender'] else 'male'}\n"
            f"<b><i>📆Age:</i></b> {reported_data['age']}\n"
            f"<b><i>📍Location:</i></b> {reported_data['origin']}\n\n"
            f"<b><i>🏓Interests:</i></b> {', '.join(reported_data['interests'])}\n\n"
            f"<b><i>👋Brief Intro:</i></b> {reported_data['bio']}\n\n"
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

@main_router.callback_query_handler(lambda c: 'wrong contact info' in c.data)
async def wrong_contact_info_report(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return

    reported_user_id = callback_query.data.split()[3]
    reported_data = await fetch_user_data(reported_user_id)
    reporting_data = await fetch_user_data(callback_query.from_user.id)
    await callback_query.message.answer("Thank you for reporting incorrect contact information.")
    await bot.send_message(
        chat_id=admin_id,
        text=(
            f"Reporter: {reporting_data['name']} {reporting_data['contact']} {reporting_data['user_id']}\n"
            f"Reason: Wrong Contact Info\n"
            f"Reported:\n"
            f"<b><i>👤Name:</i></b> {reported_data['name']}\n"
            f"<b><i>🌟Gender:</i></b> {'female' if not reported_data['gender'] else 'male'}\n"
            f"<b><i>📆Age:</i></b> {reported_data['age']}\n"
            f"<b><i>📍Location:</i></b> {reported_data['origin']}\n\n"
            f"<b><i>🏓Interests:</i></b> {', '.join(reported_data['interests'])}\n\n"
            f"<b><i>👋Brief Intro:</i></b> {reported_data['bio']}\n\n"
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

@main_router.callback_query_handler(lambda c: 'back' in c.data)
async def go_back(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return
    await callback_query.message.answer("Returning to menu.", reply_markup=create_main_menu())

@main_router.callback_query_handler(lambda c: 'ban' in c.data)
async def ban_user(callback_query: types.CallbackQuery):
    reported_id = callback_query.data.split()[1]
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer(f"User {reported_id} has been banned permanently.")
    supabase.table("telegram").update({"is_banned": True}).eq("id", reported_id).execute()

@main_router.callback_query_handler(lambda c: 'disapprove' in c.data)
async def disapprove_report(callback_query: types.CallbackQuery):
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer("The ban report has been disapproved.")

@main_router.callback_query_handler(lambda c: 'next' in c.data)
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
                f"<b><i>👋Brief Intro:</i></b> {found_user['bio']}"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Match 🎯", callback_data=f'match {found_user["user_id"]}'),
                        InlineKeyboardButton(text="Next ➡️", callback_data=f'next')
                    ],
                    [
                        InlineKeyboardButton(text="Report", callback_data=f'report {found_user["user_id"]}'),
                        InlineKeyboardButton(text="Menu", callback_data='menu')
                    ]
                ]
            )
        )
    else:
        await callback_query.message.answer(MSG_NO_MATCH)

@main_router.callback_query_handler(lambda c: 'accept' in c.data)
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
    match_user_info = await bot.get_chat(match_user_id)
    current_user_info = await bot.get_chat(match_user_id)
    match_username = match_user_info.username or "Username not set"
    current_username = current_user_info.username or "Username not set"
    
    await bot.send_message(
        chat_id=match_user_id,
        text=(
            f"Congratulations! You've got a match.\n"
            f"<b><i>Here is your match's profile:</i></b>\n\n"
            f"<b><i>👤Name:</i></b> {current_user_data['name']}\n"
            f"<b><i>🌟Gender:</i></b> {gender}\n"
            f"<b><i>📆Age:</i></b> {current_user_data['age']}\n"
            f"<b><i>📍Location:</i></b> {current_user_data['origin']}\n\n"
            f"<b><i>🏓Interests:</i></b> {', '.join(current_user_data['interests'])}\n\n"
            f"<b><i>👋Intro:</i></b> {current_user_data['bio']}\n\n"
            f"<b><i>📝Contact:</i></b> @{current_username} {current_user_data['contact']}"
        ),
        parse_mode="HTML"
    )
    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=(
            f"Congratulations! You've got a match.\n"
            f"<b><i>Here is your match's profile:</i></b>\n\n"
            f"<b><i>👤Name:</i></b> {match_user_data['name']}\n"
            f"<b><i>🌟Gender:</i></b> {'female' if not match_user_data['gender'] else 'male'}\n"
            f"<b><i>📆Age:</i></b> {match_user_data['age']}\n"
            f"<b><i>📍Location:</i></b> {match_user_data['origin']}\n\n"
            f"<b><i>🏓Interests:</i></b> {', '.join(match_user_data['interests'])}\n\n"
            f"<b><i>👋Intro:</i></b> {match_user_data['bio']}\n\n"
            f"<b><i>📝Contact:</i></b> @{match_username} {match_user_data['contact']}"
        ),
        parse_mode="HTML"
    )

@main_router.callback_query_handler(lambda c: 'reject' in c.data)
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
            "Unfortunately, your match request was declined.\n\n"
            "Keep trying, and consider updating your profile for better matches."
        ),
        parse_mode="HTML"
    )
    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text="<b>We appreciate your decision.</b>",
        parse_mode="HTML"
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
    msg = await message.answer(
        profile_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Edit", callback_data="edit")],
                [InlineKeyboardButton(text="Save and Return", callback_data="save")]
            ]
        ),
        parse_mode="HTML"
    )
    await state.update_data(prev_message_id=msg.message_id)

@edit_router.callback_query_handler(F.data == "save")
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

@edit_router.callback_query_handler(F.data == "edit")
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

@edit_router.callback_query_handler(F.data == "edit_interests")
async def process_edit_interests_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.edit_interests)
    await state.update_data(selected_interests=[])
    
    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(text=category, callback_data=f"cat_{category}")])
    keyboard.append([InlineKeyboardButton(text="Done ✅", callback_data="done_interests")])
    
    await callback.message.answer(
        "<b>Select a category:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()

@edit_router.callback_query_handler(F.data.startswith("cat_"))
async def select_category(callback: types.CallbackQuery, state: FSMContext):
    category_name = callback.data.split("_", 1)[1]
    data = await state.get_data()
    selected_interests = data.get('selected_interests', [])
    keyboard = [
        [InlineKeyboardButton(
            text=f"✅ All {category_name}" if category_name in selected_interests else f"All {category_name}",
            callback_data=f"toggle_cat_{category_name}"
        )]
    ]
    for interest in categories[category_name]:
        text = f"✅ {interest}" if interest in selected_interests else interest
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"intr_{category_name}_{interest}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_to_categories")])
    
    await callback.message.edit_text(
        f"<b>{category_name}:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()

@edit_router.callback_query_handler(F.data.startswith("toggle_cat_"))
async def toggle_category(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data.split("_", 2)[2]
    data = await state.get_data()
    selected_interests = data.get('selected_interests', [])
    if category in selected_interests:
        selected_interests.remove(category)
    else:
        selected_interests.append(category)
    await state.update_data(selected_interests=selected_interests)
    keyboard = [
        [InlineKeyboardButton(
            text=f"✅ All {category}" if category in selected_interests else f"All {category}",
            callback_data=f"toggle_cat_{category}"
        )]
    ]
    for interest in categories[category]:
        text = f"✅ {interest}" if interest in selected_interests else interest
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"intr_{category}_{interest}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_to_categories")])
    
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@edit_router.callback_query_handler(F.data.startswith("intr_"))
async def toggle_interest(callback: types.CallbackQuery, state: FSMContext):
    _, category, interest = callback.data.split("_", 2)
    data = await state.get_data()
    selected_interests = data.get('selected_interests', [])
    if interest in selected_interests:
        selected_interests.remove(interest)
    else:
        selected_interests.append(interest)
    await state.update_data(selected_interests=selected_interests)
    keyboard = []
    for intr in categories[category]:
        text = f"✅ {intr}" if intr in selected_interests else intr
        keyboard.append([InlineKeyboardButton(text=text, callback_data=f"intr_{category}_{intr}")])
    keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_to_categories")])
    
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@edit_router.callback_query_handler(F.data == "back_to_categories")
async def back_to_categories(callback: types.CallbackQuery, state: FSMContext):
    keyboard = []
    for category in categories:
        keyboard.append([InlineKeyboardButton(text=category, callback_data=f"cat_{category}")])
    keyboard.append([InlineKeyboardButton(text="Done ✅", callback_data="done_interests")])
    
    await callback.message.edit_text(
        "<b>Select a category:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()

@edit_router.callback_query_handler(F.data.in_( {"edit_age", "edit_intro", "edit_contact"} ))
async def process_edit_callback(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "edit_age":
        await state.set_state(Form.edit_age)
        await callback_query.message.answer("<b>📅 Please enter your new age:</b>", parse_mode='HTML')
    elif callback_query.data == "edit_intro":
        await state.set_state(Form.edit_intro)
        await callback_query.message.answer("<b>💬 Please enter your new introduction:</b>", parse_mode='HTML')
    elif callback_query.data == "edit_contact":
        await state.set_state(Form.edit_contact)
        await callback_query.message.answer("<b>📬 Please enter your new contact info:</b>", parse_mode='HTML')
    await callback_query.answer()

@edit_router.message(Form.edit_age)
async def process_edit_age(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    age = message.text
    if not age.isdigit():
        await message.answer("⚠️ <b>Please enter a valid number.</b>", parse_mode='HTML')
        return
    await state.update_data(age=age)
    user_id = message.from_user.id
    supabase.table("telegram").update({"age": age}).eq("user_id", user_id).execute()

    await message.answer("✅ <b>Your age has been updated.</b>", parse_mode='HTML')
    await create_edit_profile(message, state)

@edit_router.callback_query_handler(F.data == "done_interests")
async def done_interests(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_interests = data.get('selected_interests', [])
    if len(selected_interests) < 5 or len(selected_interests) > 10:
        await callback.answer("⚠️ Please select between 5 and 10 interests or categories.", show_alert=True)
        return

    user_id = callback.from_user.id
    supabase.table("telegram").update({"interests": selected_interests}).eq("user_id", user_id).execute()

    await callback.message.delete()
    await callback.message.answer("✅ <b>Interests updated successfully!</b>", parse_mode="HTML")
    await create_edit_profile(callback.message, state)

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

    await message.answer("✅ <b>Your contact info has been updated.</b>", parse_mode='HTML')
    await create_edit_profile(message, state)

@profile_router.message(Form.name)
async def process_name(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    await state.update_data(name=message.text)
    await state.set_state(Form.gender)
    await message.answer(
        "<b>🔎 What is your gender?</b>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Male"), KeyboardButton(text="Female")]],
            resize_keyboard=True,
        ),
        parse_mode='HTML'
    )

@profile_router.message(Form.gender)
async def process_gender(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    if message.text not in ['Male', 'Female']:
        await message.answer("⚠️ <b>Please choose a valid option: Male or Female.</b>", parse_mode='HTML')
        return
    await state.update_data(gender=message.text)
    await state.set_state(Form.age)
    await message.answer(
        "<b>🔎 How old are you?</b>\n<i>Enter a valid number.</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@profile_router.message(Form.age)
async def process_age(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

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
    await state.update_data(location=message.text)

@profile_router.message(Form.interests)
async def process_interests(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    interests_text = message.text
    interests = [interest.strip() for interest in interests_text.split(',') if interest.strip()]
    if len(interests) < 5 or len(interests) > 10:
        await message.answer("⚠️ <i>Please list 5 to 10 interests, separated by commas.</i>", parse_mode='HTML')
        return
    await state.update_data(interests=interests)
    await state.set_state(Form.intro)
    await message.answer(
        "<b>🔎 Write briefly about yourself, this will be your intro.</b>\n<i>Include any info (test scores, achievements, etc.).</i>",
        parse_mode='HTML'
    )

@profile_router.message(Form.intro)
async def process_intro(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    intro = message.text
    if await check_for_char_length(message, intro):
        return
    await state.update_data(intro=intro)
    await state.set_state(Form.contact)
    await message.answer(
        "<b>🔎 Provide your contact information (e.g., Telegram username, email).</b>\n<i>This will be shared after matching.</i>",
        parse_mode='HTML'
    )

@profile_router.message(Form.contact)
async def process_contact(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    contact_info = f"(telegram username: @{message.from_user.username}) {message.text}"
    await state.update_data(contact=contact_info)
    user_data = await fetch_user_data(message.from_user.id) or {}
    response_message = await process_profile_creation(state, user_data, message.from_user.id)
    await message.answer(response_message, reply_markup=create_main_menu(), parse_mode='Markdown')

@main_router.message(Command("send_all"))
async def send_all_command(message: types.Message):
    if message.from_user.id == int(admin_id):
        broadcast_content = message.text[len("/send_all "):].strip()
        if not broadcast_content:
            await message.answer("Please provide a message to broadcast after /send_all.")
            return
        
        users = supabase.table("telegram").select("user_id").eq("is_active", True).execute().data
        for user_id in users:
            try:
                await message.bot.send_message(chat_id=user_id["user_id"], text=broadcast_content)
            except Exception as e:
                print(f"Failed to send message to {user_id}: {e}")

        await message.answer("The message has been broadcast.")
    else:
        await message.answer("You are not authorized to use this command.")

if __name__ == '__main__':
    import asyncio
    asyncio.run(dp.start_polling(bot))
