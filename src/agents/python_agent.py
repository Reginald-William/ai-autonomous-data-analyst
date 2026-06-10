import logging
import pandas as pd
import sys
from io import StringIO
from src.services.llm_service import get_llm_client, MODEL_NAME
from src.services.rag_service import retrieve_context
from fastapi import HTTPException
import time

logger = logging.getLogger(__name__)

class PythonAgent:
    def __init__(self):
        self.client = get_llm_client()
        self.model = MODEL_NAME
        self.max_attempts = 3

    def clean_code(self, code: str) -> str:
        return code.replace("```python", "").replace("```", "").strip()

    def execute_code(self, code: str, file_path: str) -> str:
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

    def get_csv_context(self, file_path: str) -> str:
        df = pd.read_csv(file_path)
        context = f"Columns: {list(df.columns)}\n"
        # context += f"Data types: {dict(df.dtypes)}\n" Too confusing for LLM, so we convert to string
        context += f"Data types: { {col: str(dtype) for col, dtype in df.dtypes.items()} }\n"
        context += f"Sample rows:\n{df.head(3).to_string()}"
        return context 
    
    def generate_code(self, question: str, file_path: str, rag_context: str = "") -> str:
        csv_context = self.get_csv_context(file_path)

        prompt = f"""
        You are a data analyst. You have access to a CSV file with the following structure:

        {csv_context}

        Additional business context:
        {rag_context}

        The user is asking: {question}

        Write Python code using pandas to answer this question.
        Always write actual Python code, never answer the question directly.
        Even if the answer seems simple, always write Python code to compute it.
        Always print the final result using print().
        Make sure the last line of your code is always a print statement.
        The dataframe is already loaded as 'df'.
        Return only the Python code, nothing else.
        """

        try:
            logger.info("LLM call started")
            llm_start = time.time()
            
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,  # Lower temperature for more deterministic output
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst who writes clean Python code."},
                    {"role": "user", "content": prompt}
                ]
            )

            logger.info(f"LLM call completed in {round(time.time() - llm_start, 2)}s")
            
            generated_code = response.choices[0].message.content
            return generated_code
    
        except Exception as e:
            logger.error(f"Groq API call failed: {str(e)}")
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable. Please try again later.")

    def fix_code(self, question: str, failed_code: str, error: str, file_path: str, rag_context: str = "") -> str:
        csv_context = self.get_csv_context(file_path)
    
        prompt = f"""
        You are a data analyst. You have access to a CSV file with the following structure:
        
        {csv_context}

        Additional business context:
        {rag_context}
        
        The user is asking: {question}
        
        You previously generated this code:
        {failed_code}
        
        But it failed with this error:
        {error}
        
        Fix the code and return only the corrected Python code, nothing else.
        The dataframe is already loaded as 'df'.
        Always print the final result using print().
        Make sure the last line of your code is always a print statement which prints the output.
        """
    
        try:
            logger.info("LLM error fix call started")
            llm_start = time.time()

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst who writes clean Python code."},
                    {"role": "user", "content": prompt}
                ]
            )

            logger.info(f"LLM error fix call completed in {round(time.time() - llm_start, 2)}s")
            
            generated_code = response.choices[0].message.content
            return generated_code
        
        except Exception as e:
            logger.error(f"Groq API call failed: {str(e)}")
            raise HTTPException(status_code=503, detail="AI service temporarily unavailable. Please try again later.")

    def run(self, question: str, file_path: str) -> tuple[str, int]:
        logger.info(f"Python agent running for question: {question}")

        rag_context = retrieve_context(question)
        generated_code = self.clean_code(self.generate_code(question, file_path, rag_context))
        logger.info(f"Generated code:\n{generated_code}")

        attempt = 1
        while attempt <= self.max_attempts:
            try:
                logger.info(f"Execution attempt {attempt} of {self.max_attempts}")
                result = self.execute_code(generated_code, file_path)
                logger.info("Execution successful")
                return result, attempt

            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {str(e)}")

                if attempt == self.max_attempts:
                    raise Exception(f"Python agent failed after {self.max_attempts} attempts: {str(e)}")

                generated_code = self.clean_code(self.fix_code(question, generated_code, str(e), file_path, rag_context))
                attempt += 1
