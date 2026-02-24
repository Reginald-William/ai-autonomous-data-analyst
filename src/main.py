from fastapi import FastAPI
from dotenv import load_dotenv
import logging
import os

from src.routes.ask import router as ask_router

load_dotenv()  # reads variables from a .env file and sets them in os.environ

# log info (more standard) instead of print()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__) 

app = FastAPI(
    title="Autonomous Data Analyst",
    description="AI powered data analysis agent",
    version="0.1.0"
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
