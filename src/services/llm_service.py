from dotenv import load_dotenv
load_dotenv()
from src.services.execution_service import execute_code

import os
import pandas as pd
from groq import Groq

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
    Return only the Python code, nothing else.
    """
    
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a helpful data analyst who writes clean Python code."},
            {"role": "user", "content": prompt}
        ]
    )
    
    generated_code = response.choices[0].message.content
    return execute_code(generated_code, file_path)