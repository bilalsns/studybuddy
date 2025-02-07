# routers/edit_router.py
from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from models import Form
from utils import ignore_old_messages, format_profile, check_for_bad_words, check_for_char_length, create_main_menu
from db import update_user_data, fetch_user_data

router = Router()

@router.callback_query(lambda c: c.data == "edit")
async def edit_profile(callback_query: types.CallbackQuery, state):
    await state.set_state(Form.edit_choice)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Age", callback_data="edit_age")],
        [InlineKeyboardButton(text="Interests", callback_data="edit_interests")],
        [InlineKeyboardButton(text="Intro", callback_data="edit_intro")],
        [InlineKeyboardButton(text="Contact", callback_data="edit_contact")]
    ])
    await callback_query.message.answer("What would you like to edit?", reply_markup=markup)
    await callback_query.answer()

# Handlers for each edit choice:
@router.callback_query(lambda c: c.data in {"edit_age", "edit_interests", "edit_intro", "edit_contact"})
async def process_edit_callback(callback_query: types.CallbackQuery, state):
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
        await callback_query.message.answer("<b>📬 Please enter your new contact information:</b>", parse_mode='HTML')
    await callback_query.answer()

# Then add message handlers for each state (Form.edit_age, etc.) to process the updated data
