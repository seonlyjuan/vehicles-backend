# server/app/services/storage/storage_service.py
import time
from fastapi import UploadFile, HTTPException
from app.db.supabase import get_supabase

BUCKET_NAME = "vehicle images"

async def upload_user_image(file: UploadFile, user_id: str) -> str:
    """
    Validiert und lädt ein Bild für einen bestimmten Nutzer in Supabase Storage hoch.
    Gibt den relativen Pfad der Datei zurück.
    """
    # 1. Optionale Validierung (z.B. Dateityp prüfen)
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Nur JPEG, PNG oder WebP erlaubt.")

    supabase = get_supabase()
    
    # 2. Eindeutigen Dateinamen generieren (verhindert Überschreibungen)
    file_ext = file.filename.split(".")[-1]
    file_path = f"{user_id}/{user_id}_{int(time.time())}.{file_ext}"
    
    # Datei-Inhalt lesen
    file_bytes = await file.read()

    try:
        # 3. Hochladen zu Supabase Storage
        response = supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": file.content_type}
        )
        return file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Upload: {str(e)}")