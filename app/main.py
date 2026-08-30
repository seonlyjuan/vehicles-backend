from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.security.headers import SecurityHeadersMiddleware
from app.core.security.request_limits import UploadSizeLimitMiddleware
from app.router import api_router

app = FastAPI(title="App API")

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(UploadSizeLimitMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))
if settings.enforce_https:
    app.add_middleware(HTTPSRedirectMiddleware)

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
