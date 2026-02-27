import logging
from dotenv import load_dotenv
from src.services.llm_service import ask_llm, fix_code
from src.services.execution_service import execute_code, clean_code

load_dotenv()

logger = logging.getLogger(__name__)

def analyse(question: str, file_path: str) -> str:
    max_attempts = 3
    attempt = 1
    
    logger.info(f"Starting analysis for question: {question}")
    
    # First attempt - generate and execute code
    generated_code = ask_llm(question, file_path)
    generated_code = clean_code(generated_code)
    
    while attempt <= max_attempts:
        try:
            logger.info(f"Attempt {attempt} of {max_attempts}")
            result = execute_code(generated_code, file_path)
            logger.info("Execution successful")
            return result
        
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed with error: {str(e)}")
            
            if attempt == max_attempts:
                logger.error("All attempts failed")
                return "Unable to answer your question at this time. Please try again or rephrase your question."
            
            # Fix the code and try again
            generated_code = fix_code(question, generated_code, str(e), file_path)
            generated_code = clean_code(generated_code)
            attempt += 1