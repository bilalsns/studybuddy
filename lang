import logging
from aiogram import Bot, Dispatcher, executor, types

API_TOKEN = 'BOT_TOKEN_HERE'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

categories = {
    "Test Preparation": [
        "SAT", "ACT", "IELTS", "TOEFL", "Duolingo",
        "DTM", "Milliy Sertifikat", "GRE", "GMAT"
    ],
    "Language Exams": [
        "Turkish", "Arabic", "English", "German", "French"
    ],
    "AP Classes": [
        "AP Calculus BC", "AP Calculus AB", "AP Biology", "AP Chemistry",
        "AP Microeconomics", "AP Macroeconomics", "AP Statistics",
        "AP Psychology", "AP History", "AP Physics"
    ],
    "Olympiads": [
        "Math", "Informatics", "Chemistry", "Physics", "Biology",
        "Economics", "Computer Science", "Linguistics", "History"
    ],
    "Exchange Programs": [
        "FLEX", "UGRAD", "UWC", "PASCH", "ERASMUS"
    ],
    "Summer Programs": [
        "YYGS", "YIRLI", "RSI", "PROMYS", "LaunchX",
        "NYUAD Design Lab", "SUMaC", "ROSS"
    ],
    "Scholarships": [
        "DAAD - Germany", "DSU - Italy", "GKS - Korea", "EYUF",
        "CGS - China", "Turkiye Burslari", "Stipendium Hungaricum",
        "MEXT - Japan", "Lester B. Scholarship", "UBC Scholarship"
    ],
    "Academic Support": [
        "College Application", "Extracurricular Building", "Writing Research",
        "Essay Program", "Consultation 1v1"
    ],
    "General Interests": [
        "Movies", "Art", "Music", "Sports", "Anime", "TV Shows", "Cartoons"
    ]
}

translations = {
    "uz": {
        "language_name": "O'zbekcha",
        # Kategoriya nomlari
        "Test Preparation": "Test tayyorgarligi",
        "Language Exams": "Til imtihonlari",
        "AP Classes": "AP imtihonlari",
        "Olympiads": "Olimpiadalar",
        "Exchange Programs": "Almashish dasturlari",
        "Summer Programs": "Yozgi dasturlar",
        "Scholarships": "Stipendiyalar",
        "Academic Support": "Akademik qo'llab-quvvatlash",
        "General Interests": "Umumiy qiziqishlar",
        # Chatga yuboriladigan matnlar
        "choose_language": "Tilni tanlang / Выберите язык / Select language:",
        "press_buttons": "Iltimos, tilni tanlash tugmalaridan birini bosing.",
        "switch_message": "Tilni o'zgartirish uchun, iltimos, quyidagi tugmalardan birini bosing:",
        "show_data_message": "Ma'lumotlarni ko'rsatish uchun /data buyrug'ini yuboring.",
        "chosen_lang_message": "Tanlangan til: "
    },
    "ru": {
        "language_name": "Русский",
        "Test Preparation": "Подготовка к тестам",
        "Language Exams": "Языковые экзамены",
        "AP Classes": "AP экзамены",
        "Olympiads": "Олимпиады",
        "Exchange Programs": "Программы обмена",
        "Summer Programs": "Летние программы",
        "Scholarships": "Стипендии",
        "Academic Support": "Академическая поддержка",
        "General Interests": "Общие интересы",
        "choose_language": "Tilni tanlang / Выберите язык / Select language:",
        "press_buttons": "Пожалуйста, нажмите одну из кнопок ниже для выбора языка.",
        "switch_message": "Чтобы изменить язык, пожалуйста, нажмите одну из кнопок:",
        "show_data_message": "Чтобы показать данные, введите команду /data.",
        "chosen_lang_message": "Выбранный язык: "
    },
    "en": {
        "language_name": "English",
        "Test Preparation": "Test Preparation",
        "Language Exams": "Language Exams",
        "AP Classes": "AP Classes",
        "Olympiads": "Olympiads",
        "Exchange Programs": "Exchange Programs",
        "Summer Programs": "Summer Programs",
        "Scholarships": "Scholarships",
        "Academic Support": "Academic Support",
        "General Interests": "General Interests",
        "choose_language": "Tilni tanlang / Выберите язык / Select language:",
        "press_buttons": "Please press one of the buttons below to choose a language.",
        "switch_message": "To switch the language, please press one of the buttons below:",
        "show_data_message": "Use /data to display the categories.",
        "chosen_lang_message": "Chosen language: "
    }
}

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

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_language[message.from_user.id] = "uz"

    lang_code = user_language[message.from_user.id]
    tr = translations[lang_code]

    welcome_text = f"{tr['choose_language']}\n{tr['press_buttons']}"
    await message.answer(welcome_text, reply_markup=language_keyboard())

@dp.message_handler(commands=['switch'])
async def switch_lang_command(message: types.Message):
    lang_code = user_language.get(message.from_user.id, "uz")
    tr = translations[lang_code]
    await message.answer(tr["switch_message"], reply_markup=language_keyboard())

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('lang_'))
async def process_language(callback_query: types.CallbackQuery):
    lang_code = callback_query.data.split('_')[1]  # 'uz', 'ru', yoki 'en'
    user_language[callback_query.from_user.id] = lang_code

    tr = translations[lang_code]
    confirmation_text = tr["chosen_lang_message"] + tr["language_name"]

    await bot.answer_callback_query(callback_query.id, text=confirmation_text)
    await bot.send_message(
        callback_query.from_user.id,
        tr["show_data_message"]
    )

@dp.message_handler(commands=['data'])
async def send_data(message: types.Message):
    lang_code = user_language.get(message.from_user.id, "uz")
    tr = translations[lang_code]

    text = ""
    for cat_name, items in categories.items():
        # Kategoriya nomini tarjima qilamiz (bo'lmasa, aslisini olamiz)
        localized_cat_name = tr.get(cat_name, cat_name)
        text += f"\n{localized_cat_name}:\n"
        for item in items:
            text += f" - {item}\n"

    if not text.strip():
        text = "Hozircha ma'lumotlar mavjud emas."
    await message.answer(text.strip())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

