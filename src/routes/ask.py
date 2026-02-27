from fastapi import APIRouter
from pydantic import BaseModel
from src.services.analyst_service import analyse

router = APIRouter()

class AskRequest(BaseModel):
    question: str
    file_path: str

@router.post("/ask")
def ask_question(request: AskRequest):
    result = analyse(request.question, request.file_path)
    return {"question": request.question, "result": result}