# routers/teacher_router.py
from aiogram import Router, types
from models import Form
from utils import ignore_old_messages
from config import TEXT_BECOME_TEACHER
from db import fetch_user_data, update_user_data

router = Router()

@router.message(lambda message: message.text == TEXT_BECOME_TEACHER)
async def become_teacher(message: types.Message, state):
    if await ignore_old_messages(message):
        return
    await state.set_state(Form.teacher_subjects)
    await message.answer("Please list the subjects you can teach, separated by commas.", reply_markup=ReplyKeyboardRemove())

# Add additional teacher FSM handlers (teacher_experience, teacher_price, etc.)
