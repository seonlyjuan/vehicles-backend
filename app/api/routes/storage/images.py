
from fastapi import APIRouter, UploadFile, File, Depends
from app.services.storage.storage_service import upload_user_image
from app.crud.storage.images import save_image_metadata
# Annahme: Du hast eine Dependency, die den aktuell eingeloggten User (durch Google Login) liefert
# from app.api.deps import get_current_user 

router = APIRouter(prefix="/images", tags=["Images"])

@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    # current_user: dict = Depends(get_current_user) # Beispiel für Auth
):
    user_id = "test-user-id" # Ersetze das später durch die ID aus deinem Google-Login (current_user["id"])
    
    # 1. Logik an den Service übergeben
    image_path = await upload_user_image(file, user_id)
    
    # 2. Pfad in der Datenbank speichern (CRUD)
    save_image_metadata(user_id=user_id, image_url=image_path)
    
    return {
        "message": "Bild erfolgreich hochgeladen",
        "path": image_path
    }