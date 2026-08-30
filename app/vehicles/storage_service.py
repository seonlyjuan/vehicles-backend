from collections.abc import Iterable

from app.db.supabase import get_supabase
from app.vehicles.constants import BUCKET_NAME

STORAGE_DELETE_BATCH_SIZE = 100


def remove_vehicle_files(paths: Iterable[str]) -> None:
    items = list(paths)
    for start in range(0, len(items), STORAGE_DELETE_BATCH_SIZE):
        get_supabase().storage.from_(BUCKET_NAME).remove(items[start:start + STORAGE_DELETE_BATCH_SIZE])

