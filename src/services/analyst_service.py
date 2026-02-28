import logging
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from src.services.llm_service import ask_llm, fix_code, MODEL_NAME
from src.services.execution_service import execute_code, clean_code
from src.utils.schemas import AnalysisResponse

load_dotenv()

logger = logging.getLogger(__name__)

def analyse(question: str, file_path: str) -> AnalysisResponse:
    start_time = time.time()
    max_attempts = 3
    attempt = 1

    df = pd.read_csv(file_path)
    row_count = len(df)
    column_count = len(df.columns)
    file_name = file_path.split("/")[-1]
    
    logger.info(f"Starting analysis for question: {question}")
    
    # First attempt - generate and execute code
    generated_code = ask_llm(question, file_path)
    generated_code = clean_code(generated_code)
    logger.info(f"Generated code:\n{generated_code}")  # Added for testing purposes
    
    while attempt <= max_attempts:
        try:
            logger.info(f"Attempt {attempt} of {max_attempts}")
            result = execute_code(generated_code, file_path)
            time_taken = f"{round(time.time() - start_time, 2)}s"
            logger.info("Execution successful")
            
            return AnalysisResponse(
                question=question,
                result=result,
                status="success",
                attempts=attempt,
                time_taken=time_taken,
                model_used=MODEL_NAME,
                row_count=row_count,
                column_count=column_count,
                file_name=file_name,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed with error: {str(e)}")
            
            if attempt == max_attempts:
                time_taken = f"{round(time.time() - start_time, 2)}s"
                logger.error("All attempts failed")
                
                return AnalysisResponse(
                    question=question,
                    result="Unable to answer your question at this time. Please try again or rephrase your question.",
                    status="failed",
                    attempts=attempt,
                    time_taken=time_taken,
                    model_used=MODEL_NAME,
                    row_count=row_count,
                    column_count=column_count,
                    file_name=file_name,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            
            # Fix the code and try again
            generated_code = fix_code(question, generated_code, str(e), file_path)
            generated_code = clean_code(generated_code)
            attempt += 1