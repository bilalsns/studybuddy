from supabase import create_client
from sentence_transformers import SentenceTransformer

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


