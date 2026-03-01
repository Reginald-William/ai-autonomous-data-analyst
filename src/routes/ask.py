from fastapi import APIRouter
from pydantic import BaseModel
from src.services.analyst_service import analyse
from src.utils.schemas import AnalysisResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class AskRequest(BaseModel):
    question: str
    file_path: str

@router.post("/ask", response_model=AnalysisResponse)
def ask_question(request: AskRequest):
    logger.info(f"Request received: POST /ask")
    logger.info(f"Question: {request.question} | File: {request.file_path}")
    result = analyse(request.question, request.file_path)
    logger.info(f"Request completed | Status: {result.status} | Attempts: {result.attempts} | Time: {result.time_taken}")
    return result