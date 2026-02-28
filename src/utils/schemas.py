from pydantic import BaseModel
from datetime import datetime
from typing import Optional  # Added for optional fields (not used now)

class AnalysisResponse(BaseModel):
    question: str
    result: str
    status: str
    attempts: int
    time_taken: str
    model_used: str
    row_count: int
    column_count: int
    file_name: str
    timestamp: str