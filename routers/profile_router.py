# routers/profile_router.py
from aiogram import Router, types
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from models import Form
from utils import ignore_old_messages, check_for_bad_words, check_for_char_length, format_profile
from db import fetch_user_data, update_user_data
from config import MSG_NO_PROFILE

router = Router()

@router.message(Form.name)
async def process_name(message: types.Message, state):
    if await ignore_old_messages(message):
        return
    await state.update_data(name=message.text)
    await state.set_state(Form.gender)
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Male"), KeyboardButton(text="Female")]],
        resize_keyboard=True,
    )
    await message.answer("<b>🔎 What is your gender?</b>", reply_markup=markup, parse_mode='HTML')

@router.message(Form.gender)
async def process_gender(message: types.Message, state):
    if await ignore_old_messages(message):
        return
    if message.text not in ['Male', 'Female']:
        await message.answer("⚠️ <b>Please choose a valid gender option: Male or Female.</b>", parse_mode='HTML')
        return
    await state.update_data(gender=message.text)
    await state.set_state(Form.age)
    await message.answer("<b>🔎 How old are you?</b>", parse_mode='HTML', reply_markup=ReplyKeyboardRemove())

# … add the rest of your FSM state handlers for age, location, interests, intro, contact

@router.message(Form.contact)
async def process_contact(message: types.Message, state):
    if await ignore_old_messages(message):
        return
    contact_info = f"(telegram username: @{message.from_user.username}) {message.text}"
    await state.update_data(contact=contact_info)
    
    # Process profile creation (you may call a separate function)
    user_data = await fetch_user_data(message.from_user.id) or {}
    # For example, call a helper function process_profile_creation(state, user_data, user_id)
    # and then respond with the profile and main menu:
    response_message = "**Thank you! Your profile has been created/updated.**\n\nYou can now search for a study buddy:"
    await message.answer(response_message, reply_markup=create_main_menu(), parse_mode='Markdown')
    await state.clear()
