# models.py
from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    # User profile creation/editing states
    name = State()
    gender = State()
    age = State()
    location = State()
    interests = State()
    intro = State()
    contact = State()
    # … other states (including teacher-specific states, etc.)
    
    # For teacher application
    teacher_subjects = State()
    teacher_experience = State()
    teacher_price = State()
    teacher_availability = State()
    teacher_resume = State()

    # For student searching teacher
    student_search_field = State()
    student_show_teacher = State()
    student_select_time_topic = State()

    # … add additional states as needed
