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

admin_id = "6193719398"

@main_router.callback_query(lambda c: 'wrong contact info' in c.data)
async def wrong_contact_info_report(callback_query: types.CallbackQuery):
    """
    Foydalanuvchi noto‘g‘ri aloqa maʼlumotlarini hisobot qilganda,
    adminga hisobot tafsilotlarini yuboradi.
    """
    await callback_query.message.delete()
    if await is_user_banned(callback_query.from_user.id):
        await handle_banned_user_callback(callback_query)
        return

    reported_user_id = callback_query.data.split()[3]
    reported_data = await fetch_user_data(reported_user_id)
    reporting_data = await fetch_user_data(callback_query.from_user.id)

    await callback_query.message.answer(
        "Thank you for reporting incorrect contact information. We will review the user's details."
    )

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
            f"<b><i>👋Brief Introduction:</i></b> {reported_data['bio']}\n\n"
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

@main_router.callback_query(lambda c: 'ban' in c.data)
async def ban_user(callback_query: types.CallbackQuery):
    """
    Admin tanlovi asosida foydalanuvchini doimiy ravishda bloklaydi.
    """
    reported_id = callback_query.data.split()[1]
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer(f"The user number {reported_id} was permanently banned.")
    supabase.table("telegram").update({"is_banned": True}).eq("id", reported_id).execute()

@main_router.callback_query(lambda c: 'disapprove' in c.data)
async def disapprove_report(callback_query: types.CallbackQuery):
    """
    Admin hisobotni rad etsa, foydalanuvchiga xabar yuboradi.
    """
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await callback_query.message.answer("The report for banning user was disapproved")

@main_router.message(Command("send_all"))
async def send_all_command(message: types.Message):
    """
    /send_all buyrug‘i orqali admin barcha faol foydalanuvchilarga xabar yuborishi mumkin.
    """
    if message.from_user.id == int(admin_id):
        broadcast_content = message.text[len("/send_all "):].strip()

        if not broadcast_content:
            await message.answer("Please provide a message to broadcast after the /send_all command.")
            return
        
        users = supabase.table("telegram").select("user_id").eq("is_active", True).execute().data
        for user in users:
            try:
                await message.bot.send_message(chat_id=user["user_id"], text=broadcast_content)
            except Exception as e:
                logging.error(f"Failed to send message to {user}: {e}")

        await message.answer("The message has been broadcast to all users.")
    else:
        await message.answer("You are not authorized to use this command.")
