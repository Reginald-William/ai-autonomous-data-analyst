from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import logging
import os
import asyncio

from src.routes.ask import router as ask_router
from src.services.rag_service import build_index
from src.services.session_service import cleanup_expired_sessions, cleanup_orphaned_files

load_dotenv()  # reads variables from a .env file and sets them in os.environ

# log info (more standard) instead of print()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__) 

# Background task: clean up expired sessions every 5 minutes
async def session_cleanup_loop():
    while True:
        await asyncio.sleep(300)  # wait 5 minutes
        cleanup_expired_sessions()

# Build FAISS index at startup function
@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data/uploads", exist_ok=True)
    os.makedirs("data/charts", exist_ok=True)
    cleanup_orphaned_files()
    logger.info("Building FAISS index on startup")
    build_index("docs")
    logger.info("FAISS index ready")
    asyncio.create_task(session_cleanup_loop())
    logger.info("Session cleanup background task started")
    yield


app = FastAPI(
    title="Autonomous Data Analyst",
    description="AI powered data analysis agent",
    version="0.1.0",
    lifespan=lifespan
)

# Clean 400 for malformed requests (e.g. a string sent where a file is expected)
# instead of FastAPI's default verbose 422 with internal Pydantic error details.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Request validation failed: {exc.errors()}")
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request. Please check the fields you submitted."}
    )

# Global exception handler (safety net for any unhandled exceptions)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

app.include_router(ask_router)

@app.get("/")
def root():
    logger.info("Root endpoint called")
    return {"message": "Welcome to the Autonomous Data Analyst API!"}


@app.get("/health")
def health_check():
    logger.info("Health check called")
    return {"status": "ok", "version": "0.1.0"}
