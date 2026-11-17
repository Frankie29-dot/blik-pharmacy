from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import auth, refills

app = FastAPI(title="Blik Pharmacy API", version="0.1.0")


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "service": "Blik Pharmacy API",
        "health": "/health",
        "docs": "/docs",
    }

# Only the pharmacy's own website may call this API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,  # tokens travel in the Authorization header, not cookies
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default 422 echoes the submitted values back. Strip them so phone numbers
    # and prescription numbers never appear in responses (or anything that records them).
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(refills.router)
app.include_router(auth.router)
