from fastapi import APIRouter
from pydantic import BaseModel
from src.services.llm_service import ask_llm

router = APIRouter()

class AskRequest(BaseModel):
    question: str
    file_path: str

@router.post("/ask")
def ask_question(request: AskRequest):
    result = ask_llm(request.question, request.file_path)
    return {"question": request.question, "generated_code": result}