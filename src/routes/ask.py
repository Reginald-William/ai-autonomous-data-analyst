from fastapi import APIRouter
from pydantic import BaseModel
from src.services.analyst_service import analyse
from src.utils.schemas import AnalysisResponse

router = APIRouter()

class AskRequest(BaseModel):
    question: str
    file_path: str

@router.post("/ask", response_model=AnalysisResponse)
def ask_question(request: AskRequest):
    result = analyse(request.question, request.file_path)
    return result