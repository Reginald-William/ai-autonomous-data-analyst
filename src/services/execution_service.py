import pandas as pd
import logging
from io import StringIO
import sys
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def clean_code(code: str) -> str:
    code = code.replace("```python", "").replace("```", "")
    return code.strip()


def execute_code(code: str, file_path: str) -> str:
    try:
        df = pd.read_csv(file_path)
        
        # Capture printed output
        captured_output = StringIO()
        sys.stdout = captured_output
        
        # Create a safe environment with only df available
        safe_environment = {"df": df}
        
        # Clean the code to remove any markdown formatting
        code = clean_code(code)
        
        # Execute the generated code
        exec(code, safe_environment)
        
        # Restore stdout
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        
        if not output:
            return "Code executed successfully but produced no output"
        
        logger.info(f"Execution output:\n{output}")  # Added for testing purpose
        return output
    
    except Exception as e:
        sys.stdout = sys.__stdout__
        logger.error(f"Code execution failed: {str(e)}")
        return f"Execution error: {str(e)}"