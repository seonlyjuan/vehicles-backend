from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.router import api_router
from app.core.config import settings
from app.core.request_limits import UploadSizeLimitMiddleware

app = FastAPI(title="App API")

app.add_middleware(UploadSizeLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.client_origin],
    allow_origin_regex=settings.client_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Bindet alle Server-Routen ein.
app.include_router(api_router)
