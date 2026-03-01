import pandas as pd
import logging
from io import StringIO
import sys

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
                
        # Execute the generated code
        exec(code, safe_environment)
        
        # Restore stdout
        sys.stdout = sys.__stdout__
        
        output = captured_output.getvalue()
        
        if not output:
            raise Exception("Code executed successfully but produced no output. Make sure to print the final result.")
        
        return output
    
    except Exception as e:
        sys.stdout = sys.__stdout__
        logger.error(f"Code execution failed: {str(e)}")
        raise Exception(f"Execution error: {str(e)}")