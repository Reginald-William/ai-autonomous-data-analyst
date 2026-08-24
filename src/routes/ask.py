from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from src.services.analyst_service import analyse
from src.services.session_service import create_session, get_session
from src.utils.schemas import AnalysisResponse
import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


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


@router.post("/upload", response_model=AnalysisResponse)
async def upload_and_ask(
    question: str = Form(...),
    session_id: str = Form(None),
    file: UploadFile = File(None),
):
    """
    Ask a question about a CSV file. Two ways to use this endpoint:

    1. First request — upload a CSV file and ask a question.
       The response includes a session_id. Save it for follow-up questions.

    2. Follow-up request — send session_id + question, no file needed.
       The server reuses the previously uploaded file for the session duration (30 min).
    """
    logger.info(f"Request received: POST /upload | session_id={session_id}")

    # --- Follow-up request: reuse existing session ---
    if session_id:
        session = get_session(session_id)
        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired. Please upload your file again."
            )
        file_path = session["file_path"]
        original_filename = session["original_filename"]
        logger.info(f"Reusing session {session_id} | file: {original_filename}")

    # --- First request: validate and save uploaded file ---
    else:
        if file is None:
            raise HTTPException(status_code=400, detail="No file uploaded. Please provide a CSV file.")

        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are supported.")

        # await: read all bytes from the upload.
        # The 'await' keyword means: pause here until reading is done,
        # but let other requests run in the meantime (non-blocking).
        content = await file.read()

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File size exceeds the 10MB limit.")

        # Generate a unique ID upfront so the filename and session_id match from the start
        session_id = str(uuid4())
        file_path = f"data/uploads/{session_id}.csv"

        with open(file_path, "wb") as f:
            f.write(content)

        # Validate it's a parseable CSV (nrows=0 just reads headers — fast)
        try:
            pd.read_csv(file_path, nrows=0)
        except Exception:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="File is not a valid CSV.")

        # Register the session with the already-saved file path
        original_filename = file.filename
        create_session(session_id, file_path, original_filename)
        logger.info(f"File saved: {file_path} | original: {original_filename}")

    result = analyse(question, file_path, session_id=session_id, original_filename=original_filename)
    logger.info(f"Request completed | Status: {result.status} | Attempts: {result.attempts} | Time: {result.time_taken}")
    return result
