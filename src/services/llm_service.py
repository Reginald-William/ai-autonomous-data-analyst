from dotenv import load_dotenv
load_dotenv()

import os
import time
import pandas as pd
from groq import Groq
import logging
from fastapi import HTTPException

MODEL_NAME = "llama-3.1-8b-instant"  # Using as const for now, can be made dynamic later if needed

logger = logging.getLogger(__name__)

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

def get_csv_context(file_path: str) -> str:
    df = pd.read_csv(file_path)
    context = f"Columns: {list(df.columns)}\n"
    # context += f"Data types: {dict(df.dtypes)}\n" Too confusing for LLM, so we convert to string
    context += f"Data types: { {col: str(dtype) for col, dtype in df.dtypes.items()} }\n"
    context += f"Sample rows:\n{df.head(3).to_string()}"
    return context


def ask_llm(question: str, file_path: str) -> str:
    context = get_csv_context(file_path)
    
    prompt = f"""
    You are a data analyst. You have access to a CSV file with the following structure:
    
    {context}
    
    The user is asking: {question}
    
    Write Python code using pandas to answer this question.
    The dataframe is already loaded as 'df'.
    Always write actual Python code, never answer the question directly.
    Even if the answer seems simple, always write Python code to compute it.
    Never return anything other than Python code. Do not include any explanations, comments, or markdown formatting.
    Only return the raw Python code.
    Always print the final result using print().
    Make sure the last line of your code is always a print statement which prints the output.
    """
    
    try:
        logger.info("LLM call started")
        llm_start = time.time()
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
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

# If the generated code fails, we can use the error message to ask the LLM to fix it
def fix_code(question: str, failed_code: str, error: str, file_path: str) -> str:
    context = get_csv_context(file_path)
    
    prompt = f"""
    You are a data analyst. You have access to a CSV file with the following structure:
    
    {context}
    
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

        response = client.chat.completions.create(
            model=MODEL_NAME,
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