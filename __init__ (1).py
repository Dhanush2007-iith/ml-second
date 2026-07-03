import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database import Base, engine, SessionLocal
from . import seed
from .routers import auth, dashboard, mood, assessments, chat, resources, appointments, peer, notifications, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mindbridge")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MindBridge API",
    description="AI-powered psychological intervention platform for colleges.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        seed.run_seed(db)
        logger.info("Database ready.")
    finally:
        db.close()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation failed", "errors": exc.errors()},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Something went wrong on our end. Please try again."},
    )


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(mood.router)
app.include_router(assessments.router)
app.include_router(chat.router)
app.include_router(resources.router)
app.include_router(appointments.router)
app.include_router(peer.router)
app.include_router(notifications.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "MindBridge API", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}
