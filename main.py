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
from sentence_transformers import SentenceTransformer
from sort import *

# Timezone configuration
server_timezone = "Asia/Tashkent"
current_time = datetime.now(ZoneInfo(server_timezone))
print(current_time)

# Supabase configuration
url = "https://pghlbddjvcllgcqpvvxl.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBnaGxiZGRqdmNsbGdjcXB2dnhsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTk4MTU1MTEsImV4cCI6MjAzNTM5MTUxMX0.TyymllzljjCQsd7kUUGQ_zPgC_GLnkeV64KujZRyrQU"
supabase = create_client(url, key)

# Initialize SentenceTransformer model
model = SentenceTransformer("paraphrase-MiniLM-L3-v2")

# Bot configuration
API_TOKEN = '7495888476:AAGymgKPkmjYXISWNGBMtsx1XD3JC8KP7XA'
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
TEXT_LOOKING_FOR_TEACHERS = 'Looking for Teachers'
TEXT_BECOME_TEACHER = 'Become a Teacher'

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
    
    # For teacher application (removed name, age, location states)
    teacher_subjects = State()
    teacher_experience = State()
    teacher_price = State()
    teacher_availability = State()
    teacher_resume = State()
    
    # For student searching for teachers
    student_search_field = State()
    student_show_teacher = State()
    student_select_time_topic = State()


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


async def show_teacher(message, state):
    data = await state.get_data()
    teachers = data.get('teachers')
    current_teacher_index = data.get('current_teacher_index', 0)

    if current_teacher_index >= len(teachers):
        await message.answer("No more teachers found.")
        await state.clear()
        return

    teacher = teachers[current_teacher_index]

    # Format teacher profile for display
    teacher_profile = format_teacher_profile(teacher)

    # Send the teacher profile to the student
    await message.answer(
        teacher_profile,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Choose this teacher", callback_data="choose_teacher"),
                    InlineKeyboardButton(text="Next", callback_data="next_teacher")
                ]
            ]
        ),
        parse_mode='HTML'
    )


# Helper function to create reply markup
def create_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=TEXT_SEARCH_BUDDY),
                KeyboardButton(text=TEXT_EDIT_PROFILE),
                KeyboardButton(text=TEXT_MY_TOKENS)
            ],
            [
                KeyboardButton(text=TEXT_LOOKING_FOR_TEACHERS),
                KeyboardButton(text=TEXT_BECOME_TEACHER)
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
    if referrer_id != None:
        referrer_data = await fetch_user_data(referrer_id)
        if referrer_data:
            supabase.table("telegram").update({
                "referral_count": referrer_data["referral_count"] + 1,
                "token": referrer_data["token"] + 9
            }).eq("user_id", referrer_id).execute()

    await state.clear()
    await state.set_state(None)
    return "**Thank you! Your profile has been created/updated.**\n\nYou can now search for a study buddy:"

# Function to perform matchmaking using embeddings
async def find_best_match(request, user_data):
    # Fetch data from the database
    match = supabase.table("telegram").select("*", count="exact").order('id').execute().data
    interests = supabase.table("telegram").select("interests", count="exact").order('id').execute().data
    banned = supabase.table("telegram").select("id", count="exact").eq("is_banned", "True").execute().data
    
    # Create banned list (ensure consistent data type)
    banned_list = {str(b['id']) for b in banned}
    print(banned_list)
    
    # Prepare parameters for model encoding
    param = [" ".join(interest['interests']) for interest in interests]
    
    # Encode query and interests
    query_embedding = model.encode(request)
    passage_embeddings = model.encode(param)
    
    # Compute similarity results
    result = [(score, idx + 1) for idx, score in enumerate(model.similarity(query_embedding, passage_embeddings)[0])]
    result.sort(reverse=True)
    
    # Convert user history to a set of strings
    if user_data['history'] is None:
        history = []
    else:
        history = {str(id) for id in user_data['history']}
        
    print(history)
    print(result)
    
    # Filter results - Ensure that IDs are consistently compared as strings
    filtered_results = [
        str(item[1]) 
        for item in result 
        if str(item[1]) not in history and str(item[1]) != str(user_data['id']) and str(item[1]) not in banned_list
    ]
    
    print(filtered_results)
    
    # Handle case where no new matches are found
    if not filtered_results:
        filtered_results = [
            str(item[1]) 
            for item in result 
            if str(item[1]) != str(user_data['id']) and str(item[1]) not in banned_list
        ]
        formatted_history = f"{{{filtered_results[0]}}}"
    else:
        # Ensure user_data['history'] is a list before updating it
        if 'history' not in user_data or not user_data['history']:
            user_data['history'] = []

        # Add the new result to the history
        updated_history = user_data['history'] + [filtered_results[0]]
        user_data['history'] = updated_history
        
        # Format the history for output
        formatted_history = f"{{{','.join(map(str, user_data['history']))}}}"

    
    # Update the database with the new history, last search time, and token count
    supabase.table("telegram").update({"history": formatted_history}).eq("user_id", user_data["user_id"]).execute()
    supabase.table("telegram").update({"token": user_data["token"]-1}).eq("user_id", user_data["user_id"]).execute()
    supabase.table("telegram").update({"last_search": datetime.now(ZoneInfo(server_timezone)).isoformat()}).eq("user_id", user_data["user_id"]).execute()
    
    # Return the best match
    print(result)
    print(filtered_results)
    print(match[int(filtered_results[0]) - 1])
    return match[int(filtered_results[0]) - 1]

# Ignore old messages
bot_startup_time = current_time
async def ignore_old_messages(message: types.Message):
    if message.date < bot_startup_time:
        await message.answer("This message was sent while the bot was offline and cannot be processed.")
        return True
    return False


# bad words checker
async def check_for_bad_words(message: types.Message, text_to_check: str) -> bool:
    print(contains_dirty_words(text_to_check))
    if contains_dirty_words(text_to_check):
        await message.answer("Please avoid using inappropriate language. Try again.")
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
    await state.update_data(referrer_id = referrer_id)

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
        if (difference.days > 0): 
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

# Handler for students looking for teachers
@main_router.message(F.text == TEXT_LOOKING_FOR_TEACHERS)
async def looking_for_teachers(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    if await is_user_banned(message.from_user.id):
        await handle_banned_user(message)
        return

    # Ask the student to choose a particular field of interest
    await state.set_state(Form.student_search_field)
    await message.answer(
        "Please choose a field of interest:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Tests (IELTS, APs, SAT, A-Levels, etc.)")],
                [KeyboardButton(text="Academics (Math, Biology, English, etc.)")],
                [KeyboardButton(text="College Admissions")],
            ],
            resize_keyboard=True,
        )
    )

@main_router.message(Form.student_search_field)
async def process_student_search_field(message: types.Message, state: FSMContext):
    field_of_interest = message.text
    await state.update_data(field_of_interest=field_of_interest)
    
    teachers = fetch_teachers(field_of_interest)
    if not teachers:
        await message.answer("No teachers found matching your criteria.")
        await state.clear()
        return

    await state.update_data(teachers=teachers, current_teacher_index=0)
    await state.set_state(Form.student_show_teacher)
    await show_teacher(message, state)

@main_router.message(Form.student_show_teacher)
async def handle_unexpected_message(message: types.Message, state: FSMContext):
    # Inform the user that they should use the provided buttons
    await message.answer("Please use the buttons provided to navigate through the teachers.")

@main_router.callback_query(Form.student_show_teacher, lambda c: c.data == "choose_teacher")
async def choose_teacher(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = await state.get_data()
    current_teacher_index = data.get('current_teacher_index', 0)
    teachers = data.get('teachers')
    teacher = teachers[current_teacher_index]

    # Save the selected teacher
    await state.update_data(selected_teacher=teacher)
    await state.set_state(Form.student_select_time_topic)
    await callback_query.message.answer("Please enter the time and topic you would like to study with this teacher.")

@main_router.callback_query(Form.student_show_teacher, lambda c: c.data == "next_teacher")
async def next_teacher(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    # Update the current teacher index
    data = await state.get_data()
    current_teacher_index = data.get('current_teacher_index', 0) + 1
    await state.update_data(current_teacher_index=current_teacher_index)

    # Show the next teacher
    await show_teacher(callback_query.message, state)

@main_router.message(Form.student_select_time_topic)
async def process_student_select_time_topic(message: types.Message, state: FSMContext):
    time_topic = message.text
    await state.update_data(time_topic=time_topic)

    # Send request to the teacher
    data = await state.get_data()
    teacher = data.get('selected_teacher')
    student = message.from_user

    # Send message to the teacher
    teacher_user_id = teacher['user_id']

    await bot.send_message(
        chat_id=teacher_user_id,
        text=(
            f"You have a new teaching request from {student.full_name} (@{student.username}).\n"
            f"Time and Topic: {time_topic}\n"
            "Do you accept this request?"
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Accept", callback_data=f"accept_request {student.id}"),
                    InlineKeyboardButton(text="Reject", callback_data=f"reject_request {student.id}")
                ]
            ]
        )
    )

    await message.answer("Your request has been sent to the teacher. Please wait for their response.")
    await state.clear()

# Handlers for teacher's response
@main_router.callback_query(lambda c: c.data.startswith("accept_request"))
async def accept_request(callback_query: types.CallbackQuery):
    await callback_query.answer()
    student_user_id = int(callback_query.data.split()[1])

    # Send contact information to both parties
    teacher_user_id = callback_query.from_user.id

    # Fetch teacher and student data
    teacher_data = await fetch_teacher_data(teacher_user_id)
    student_data = await fetch_user_data(student_user_id)

    # Send teacher contact to student
    await bot.send_message(
        chat_id=student_user_id,
        text=(
            f"The teacher has accepted your request.\n"
            f"Contact info: {teacher_data['contact']}"
        )
    )

    # Send student contact to teacher
    await bot.send_message(
        chat_id=teacher_user_id,
        text=(
            f"You have accepted the request from {student_data['name']}.\n"
            f"Contact info: {student_data['contact']}"
        )
    )

@main_router.callback_query(lambda c: c.data.startswith("reject_request"))
async def reject_request(callback_query: types.CallbackQuery):
    await callback_query.answer()
    student_user_id = int(callback_query.data.split()[1])

    # Notify the student
    await bot.send_message(
        chat_id=student_user_id,
        text="Unfortunately, the teacher has rejected your request."
    )

    # Acknowledge the teacher
    await callback_query.message.answer("You have rejected the request.")





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
        await message.answer(f"📝<b>What is your name?</b>", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        return

    if user_data['token'] > 0:
        request = ' '.join(user_data["interests"])

        # Add 9 tokens daily
        timestamptz_str = user_data['last_search']
        if timestamptz_str is not None:
            last_datetime = datetime.fromisoformat(timestamptz_str)
        else:
            # Handle the case when timestamptz_str is None
            # You can set a default value or return an error message
            last_datetime = None  # or some default behavior
            await message.answer("No valid timestamp found for this user.")
            return  # Optionally return early if there's nothing to process
        
        difference = datetime.now(ZoneInfo(server_timezone)) - last_datetime
        if (difference.days > 0): 
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
                [   # InlineKeyboardButton(text="else", callback_data=f'report else {report_user_id}'),
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

    # Fetch user info using get_chat
    user_info = await bot.get_chat(reported_user_id)
    # Check if username is available
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
    await callback_query.message.answer(f"The report for baning user was disapproved")

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
    if (difference.days > 0): 
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
    # Check if username is available
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
    
    # Fetch user info using get_chat
    match_user_info = await bot.get_chat(match_user_id)
    current_user_info = await bot.get_chat(match_user_id)
    # Check if username is available
    match_username = match_user_info.username or "Username not set"
    current_username = current_user_info.username or "Username not set"
    
    await bot.send_message(
        chat_id=match_user_id,
        text=(
            f"Unfortunately, your request for matching was declined 😔. \n\n"
            f"People come and go. It really doesn't matter; what really matters is how you learn from the experience. And remember, blocking the bot doesn't help.\n\n"
            f"<b>Fortunately, you still can find the right person using our bot 🥳.</b>\n\n"
            f"PS: To get more matches, you can improve your profile."
        ),
        parse_mode="HTML",
    )
    await bot.send_message(
        chat_id=callback_query.from_user.id,
        text=(
            f"<b>We appreciate your desicion.</b>"
        ),
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
        await message.answer(f"📝<b>What is your name?</b>", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        return

    profile_text = await format_profile(user_data)
    msg = await message.answer(profile_text, reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Edit", callback_data="edit")],
            [InlineKeyboardButton(text="Save and Return", callback_data="save")]
        ]
    ), parse_mode="HTML"
    )
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
    if await check_for_bad_words(message, interests_text):
        return
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
    if await check_for_bad_words(message, intro):
        return
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
    supabase.table("telegram").update({"contact": contact}).eq("user_id", user_id).execute()

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
    if await check_for_bad_words(message, interests_text):
        return
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
    if await check_for_bad_words(message, intro):
        return
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
    # Check if the user is the admin
    if message.from_user.id == int(admin_id):
        # Get the message after the "/send_all " command
        broadcast_content = message.text[len("/send_all "):].strip()

        if not broadcast_content:
            await message.answer("Please provide a message to broadcast after the /send_all command.")
            return
        
        # Broadcast the message to all users in users    
        users = supabase.table("telegram").select("user_id").eq("is_active", True).execute().data
        for user_id in users:
            try:
                await message.bot.send_message(chat_id=user_id["user_id"], text=broadcast_content)
            except Exception as e:
                print(f"Failed to send message to {user_id}: {e}")

        # Notify the admin that the message has been broadcasted
        await message.answer("The message has been broadcast to all users.")
    else:
        await message.answer("You are not authorized to use this command.")


# Handler for teachers to submit applications
@main_router.message(F.text == TEXT_BECOME_TEACHER)
async def become_teacher(message: types.Message, state: FSMContext):
    if await ignore_old_messages(message):
        return

    if await is_user_banned(message.from_user.id):
        await handle_banned_user(message)
        return

    # Start the teacher application process
    await state.set_state(Form.teacher_subjects)
    await message.answer("Please list the subjects you can teach, separated by commas.", reply_markup=ReplyKeyboardRemove())

@main_router.message(Form.teacher_subjects)
async def process_teacher_subjects(message: types.Message, state: FSMContext):
    subjects = [subject.strip() for subject in message.text.split(',') if subject.strip()]
    await state.update_data(teacher_subjects=subjects)
    await state.set_state(Form.teacher_experience)
    await message.answer("Please describe your teaching experience.")

@main_router.message(Form.teacher_experience)
async def process_teacher_experience(message: types.Message, state: FSMContext):
    await state.update_data(teacher_experience=message.text)
    await state.set_state(Form.teacher_price)
    await message.answer("Please provide your price per hour.")

@main_router.message(Form.teacher_price)
async def process_teacher_price(message: types.Message, state: FSMContext):
    await state.update_data(teacher_price=message.text)
    await state.set_state(Form.teacher_availability)
    await message.answer("Please provide your availability.")

@main_router.message(Form.teacher_availability)
async def process_teacher_availability(message: types.Message, state: FSMContext):
    await state.update_data(teacher_availability=message.text)
    await state.set_state(Form.teacher_resume)
    await message.answer("Please upload your resume or provide a link to it.")

@main_router.message(Form.teacher_resume)
async def process_teacher_resume(message: types.Message, state: FSMContext):
    await state.update_data(teacher_resume=message.text)
    # Now, save the teacher application and notify admin for verification
    data = await state.get_data()

    # Create the teacher application data
    teacher_application = {
        'user_id': message.from_user.id,
        'name': data.get('name', 'N/A'),
        'subjects': data['teacher_subjects'],
        'experience': data['teacher_experience'],
        'price': data['teacher_price'],
        'availability': data['teacher_availability'],
        'resume': data['teacher_resume'],
        'verified': False  # Initially not verified
    }

    # Save the application to the 'telegram' table in Supabase
    supabase.table("telegram").insert(teacher_application).execute()
    contact = supabase.table("telegram").select("contact", count="exact").eq('user_id', message.from_user.id).execute().data

    
    # Notify the admin for verification
    admin_message = (
        f"📋 <b>New Teacher Application</b>\n\n"
        f"👤 <b>User ID:</b> {message.from_user.id}\n"
        f"👤 <b>Name:</b> {teacher_application['name']}\n"
        f"📚 <b>Subjects:</b> {', '.join(teacher_application['subjects'])}\n"
        f"💼 <b>Experience:</b> {teacher_application['experience']}\n"
        f"💰 <b>Price per hour:</b> {teacher_application['price']}\n"
        f"🕒 <b>Availability:</b> {teacher_application['availability']}\n"
        f"📄 <b>Resume:</b> {teacher_application['resume']}\n"
        f"📞 <b>Contact:</b> {teacher_application['contact']}\n"
    )

    await bot.send_message(
        chat_id=admin_id,
        text=admin_message,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Approve", callback_data=f"approve_teacher {message.from_user.id}"),
                    InlineKeyboardButton(text="Reject", callback_data=f"reject_teacher {message.from_user.id}")
                ]
            ]
        ),
        parse_mode='HTML'
    )

    await message.answer("Your application has been submitted. We will review it and get back to you soon.")
    await state.clear()

# Admin handlers to approve or reject teacher applications
@main_router.callback_query(lambda c: c.data.startswith("approve_teacher"))
async def approve_teacher(callback_query: types.CallbackQuery):
    teacher_user_id = int(callback_query.data.split()[1])

    # Update the 'verified' status in the 'telegram' table
    supabase.table("telegram").update({'verified': True}).eq('user_id', teacher_user_id).execute()

    # Notify the teacher
    await bot.send_message(
        chat_id=teacher_user_id,
        text="Congratulations! Your application has been approved, and you are now a verified teacher."
    )

    # Acknowledge the admin
    await callback_query.answer("Teacher application approved.")
    await callback_query.message.delete()

@main_router.callback_query(lambda c: c.data.startswith("reject_teacher"))
async def reject_teacher(callback_query: types.CallbackQuery):
    teacher_user_id = int(callback_query.data.split()[1])

    # Optionally, you can delete the application or keep it with 'verified': False
    # Here, we'll notify the teacher about the rejection

    # Notify the teacher
    await bot.send_message(
        chat_id=teacher_user_id,
        text="We regret to inform you that your teacher application has been rejected."
    )

    # Acknowledge the admin
    await callback_query.answer("Teacher application rejected.")
    await callback_query.message.delete()

# Function to fetch teachers from the 'telegram' table
def fetch_teachers(field_of_interest):
    # Fetch verified teachers matching the field of interest
    response = supabase.table("telegram").select("*").eq('verified', True).execute()
    all_teachers = response.data

    # Filter teachers based on the field of interest and their subjects
    matching_teachers = [
        teacher for teacher in all_teachers
        if field_of_interest.lower() in [subject.lower() for subject in teacher.get('subjects', [])]
    ]

    return matching_teachers

# Function to format teacher profile for display
def format_teacher_profile(teacher):
    return (
        f"📚 <b>Teacher Profile</b>\n\n"
        f"👤 <b>Name:</b> {teacher.get('name', 'N/A')}\n"
        f"📚 <b>Subjects:</b> {', '.join(teacher.get('subjects', []))}\n"
        f"💼 <b>Experience:</b> {teacher.get('experience', 'N/A')}\n"
        f"💰 <b>Price per hour:</b> {teacher.get('price', 'N/A')}\n"
        f"🕒 <b>Availability:</b> {teacher.get('availability', 'N/A')}\n"
        f"📄 <b>Resume:</b> {teacher.get('resume', 'N/A')}\n"
    )




if __name__ == '__main__':
    import asyncio
    asyncio.run(dp.start_polling(bot))
