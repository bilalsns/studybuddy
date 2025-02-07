from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

# Create a global Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def fetch_user_data(user_id):
    response = supabase.table("telegram").select("*").eq("user_id", user_id).execute()
    data = response.data
    return data[0] if data else None

async def update_user_data(user_id, updates: dict):
    return supabase.table("telegram").update(updates).eq("user_id", user_id).execute()

# You can add more database helper functions (e.g., fetch_teacher_data, insert_profile, etc.)
