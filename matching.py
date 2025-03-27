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

async def fetch_users_in_batches(batch_size=100):
    """Fetch users from database in batches"""
    all_users = []
    offset = 0
    
    while True:
        batch = supabase.table("telegram").select("*").range(offset, offset + batch_size - 1).execute().data
        if not batch:
            break
        all_users.extend(batch)
        offset += batch_size
    
    return all_users

async def fetch_banned_users():
    """Fetch all banned user IDs"""
    banned = supabase.table("telegram").select("id").eq("is_banned", True).execute().data
    return {str(b['id']) for b in banned}

async def find_best_match(request, user_data):
    try:
        # Fetch all users and banned list
        all_users = await fetch_users_in_batches()
        banned_list = await fetch_banned_users()
        
        # Convert user history to a set of strings
        history = set(str(id) for id in (user_data['history'] or []))
        user_id_str = str(user_data['id'])
        
        # Filter out banned users, history, and self
        candidate_users = [
            user for user in all_users
            if (str(user['id']) not in banned_list and
                str(user['id']) not in history and
                str(user['id']) != user_id_str)
        ]
        
        # If no candidates after filtering, relax the history constraint
        if not candidate_users:
            candidate_users = [
                user for user in all_users
                if (str(user['id']) not in banned_list and
                    str(user['id']) != user_id_str)
            ]
        
        if not candidate_users:
            return None
            
        # Process in batches for embeddings
        batch_size = 100
        best_match = None
        best_score = -1
        
        for i in range(0, len(candidate_users), batch_size):
            batch = candidate_users[i:i + batch_size]
            
            # Prepare batch data
            batch_interests = [" ".join(user['interests']) for user in batch]
            
            # Encode query and batch interests
            query_embedding = model.encode(request)
            passage_embeddings = model.encode(batch_interests)
            
            # Compute similarities
            similarities = model.similarity(query_embedding, passage_embeddings)[0]
            
            # Find best match in current batch
            batch_best_idx = np.argmax(similarities)
            batch_best_score = similarities[batch_best_idx]
            
            if batch_best_score > best_score:
                best_score = batch_best_score
                best_match = batch[batch_best_idx]
        
        if not best_match:
            return None
            
        # Update user history
        new_history = list(history) + [str(best_match['id'])]
        formatted_history = f"{{{','.join(new_history)}}}"
        
        # Update database
        supabase.table("telegram").update({
            "history": formatted_history,
            "token": user_data["token"] - 1,
            "last_search": datetime.now(ZoneInfo(server_timezone)).isoformat()
        }).eq("user_id", user_data["user_id"]).execute()
        
        return best_match
        
    except Exception as e:
        print(f"Error in find_best_match: {e}")
        return None
