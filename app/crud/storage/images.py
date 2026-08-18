# server/app/crud/images.py
from app.db.supabase import get_supabase

def save_image_metadata(user_id: str, image_url: str):
    supabase = get_supabase()
    
    # Angenommen, du hast in Supabase eine Tabelle namens 'user_images'
    # mit den Spalten 'user_id' und 'image_url'
    response = supabase.table("user_images").insert({
        "user_id": user_id,
        "image_url": image_url
    }).execute()
    
    return response.data