import logging
from src.services.llm_service import ask_llm, fix_code
from src.services.execution_service import execute_code, clean_code
from src.services.rag_service import retrieve_context

logger = logging.getLogger(__name__)

class PythonAgent:
    def __init__(self):
        self.max_attempts = 3
    
    def run(self, question: str, file_path: str) -> str:
        logger.info(f"Python agent running for question: {question}")
        
        rag_context = retrieve_context(question)
        generated_code = ask_llm(question, file_path, rag_context)
        generated_code = clean_code(generated_code)
        logger.info(f"Generated code:\n{generated_code}")
        
        attempt = 1
        while attempt <= self.max_attempts:
            try:
                logger.info(f"Execution attempt {attempt} of {self.max_attempts}")
                result = execute_code(generated_code, file_path)
                logger.info("Execution successful")
                return result
            
            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {str(e)}")
                
                if attempt == self.max_attempts:
                    raise Exception(f"Python agent failed after {self.max_attempts} attempts: {str(e)}")
                
                generated_code = fix_code(question, generated_code, str(e), file_path, rag_context)
                generated_code = clean_code(generated_code)
                attempt += 1
