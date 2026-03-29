from pydantic import BaseModel
from typing import Optional, List

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
    agents_used: List[str] = []
    task_type: str = ""
    reasoning: str = ""
    chart_path: Optional[str] = None
