from supabase import create_client
from sentence_transformers import SentenceTransformer
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np

# Timezone configuration
server_timezone = "Asia/Tashkent"
current_time = datetime.now(ZoneInfo(server_timezone))

# Supabase configuration
url = "https://pghlbddjvcllgcqpvvxl.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBnaGxiZGRqdmNsbGdjcXB2dnhsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTk4MTU1MTEsImV4cCI6MjAzNTM5MTUxMX0.TyymllzljjCQsd7kUUGQ_zPgC_GLnkeV64KujZRyrQU"
supabase = create_client(url, key)

# Initialize SentenceTransformer model
model = SentenceTransformer("paraphrase-MiniLM-L3-v2")

async def fetch_candidate_users(user_data, include_history=True):
    """Fetch candidate users from the database with optimized filters"""
    user_id = str(user_data['id'])
    history = user_data.get('history', []) or []
    
    query = (
        supabase.table("telegram")
        .select("id, interests, gender, age, origin, bio, contact, user_id")
        .eq("is_banned", False)
        .neq("id", user_id)
    )
    
    if include_history and history:
        query = query.not_.in_("id", history)
    
    return query.execute().data

async def find_best_match(request, user_data):
    try:
        # Fetch candidates (first attempt excludes history)
        candidates = await fetch_candidate_users(user_data, include_history=True)
        
        # If no candidates, relax history constraint
        if not candidates:
            candidates = await fetch_candidate_users(user_data, include_history=False)
            if not candidates:
                return None
        
        # Encode all candidate interests in one batch
        candidate_interests = [" ".join(user['interests']) for user in candidates]
        query_embedding = model.encode(request)
        candidate_embeddings = model.encode(candidate_interests)
        
        # Compute similarities in one operation
        similarities = np.dot(candidate_embeddings, query_embedding.T).flatten()
        best_idx = np.argmax(similarities)
        best_match = candidates[best_idx]
        
        # Update history (manually append to array)
        new_history = user_data.get('history', []) + [str(best_match['id'])]
        
        # Update database (use raw SQL for array append if needed)
        supabase.table("telegram").update({
            "history": new_history,
            "token": user_data["token"] - 1,
            "last_search": datetime.now(ZoneInfo(server_timezone)).isoformat()
        }).eq("user_id", user_data["user_id"]).execute()
        
        return best_match
        
    except Exception as e:
        print(f"Error in find_best_match: {e}")
        return None
