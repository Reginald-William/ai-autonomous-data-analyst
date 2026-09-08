import logging
import pandas as pd
from contextlib import redirect_stdout
from io import StringIO
from src.services.llm_service import get_llm_client, get_model_for_complexity, get_retry_budget, DEFAULT_MODEL
from src.services.rag_service import retrieve_context
from fastapi import HTTPException
import time

logger = logging.getLogger(__name__)

# Added for "high" complexity only (see run()). Complexity used to also
# scale how many sample rows appeared in the prompt (PROMPT_SAMPLE_ROWS),
# but that lever died when data_context_service.py replaced the per-agent
# CSV peek with a fixed-size shared context (Phase 4) — leaving retry
# budget as the only thing that differed between medium and high, which
# only helps after a first attempt already failed. This scaffolding
# targets the actual gap: first-attempt reasoning quality on genuinely
# multi-step questions (the ones complexity=high is meant to describe),
# not just how many retries they get.
HIGH_COMPLEXITY_SCAFFOLDING = """
        This question requires combining multiple computations (e.g. trend over time,
        comparison across dimensions, or a multi-step calculation). Before writing the final
        code: identify each intermediate value you need and the order you need them in. Write
        code that computes and prints each intermediate step as well as the final answer, not
        just the final answer alone — this makes it possible to tell which step is wrong if the
        result looks incorrect.
        """


class PythonAgent:
    def __init__(self, client=None):
        self.client = client if client is not None else get_llm_client()
        self.model = DEFAULT_MODEL
        self.max_attempts = 3

    def clean_code(self, code: str) -> str:
        return code.replace("```python", "").replace("```", "").strip()

    def execute_code(self, code: str, file_path: str) -> str:
        try:
            df = pd.read_csv(file_path)

            # Create a safe environment with only df available
            safe_environment = {"df": df}

            # Capture printed output. redirect_stdout guarantees sys.stdout
            # is restored on the way out of the `with` block even if exec()
            # raises something except Exception below wouldn't catch (e.g.
            # SystemExit) — a bare reassign-then-restore-in-except doesn't
            # cover that, and under concurrent requests a raw `sys.stdout =`
            # reassignment is a shared global that a second in-flight
            # request could also be reassigning at the same time.
            captured_output = StringIO()
            with redirect_stdout(captured_output):
                exec(code, safe_environment)

            output = captured_output.getvalue()

            if not output:
                raise Exception("Code executed successfully but produced no output. Make sure to print the final result.")

            return output

        except Exception as e:
            logger.error(f"Code execution failed: {str(e)}")
            raise Exception(f"Execution error: {str(e)}")

    def generate_code(self, question: str, data_context: str = "", rag_context: str = "", complexity: str = "medium") -> str:
        prompt = f"""
        You are a data analyst. You have access to a CSV file with the following structure:

        {data_context}

        Additional business context:
        {rag_context}

        The user is asking: {question}
        {HIGH_COMPLEXITY_SCAFFOLDING if complexity == "high" else ""}
        Write Python code using pandas to answer this question.
        Always write actual Python code, never answer the question directly.
        Even if the answer seems simple, always write Python code to compute it.
        Always print the final result using print().
        Make sure the last line of your code is always a print statement.
        The dataframe is already loaded as 'df'.
        Return only the Python code, nothing else.
        Be precise about statistical operations: use .mean() for average, .sum() for total, .median() for median, .std() for standard deviation.
        When grouping by month always use pd.Grouper(key='date', freq='ME') — never use freq='M' as it is deprecated in pandas >= 2.2.
        Always convert date columns with pd.to_datetime() before any date-based grouping.
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

    def fix_code(self, question: str, failed_code: str, error: str, data_context: str = "", rag_context: str = "", complexity: str = "medium") -> str:
        prompt = f"""
        You are a data analyst. You have access to a CSV file with the following structure:

        {data_context}

        Additional business context:
        {rag_context}

        The user is asking: {question}

        You previously generated this code:
        {failed_code}

        But it failed with this error:
        {error}
        {HIGH_COMPLEXITY_SCAFFOLDING if complexity == "high" else ""}
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

    def run(self, question: str, file_path: str, complexity: str = "medium", data_context: str = "") -> tuple[str, int, str]:
        self.model = get_model_for_complexity(complexity)
        self.max_attempts = get_retry_budget(complexity)
        logger.info(f"Python agent running for question: {question} | complexity={complexity} | model={self.model} | max_attempts={self.max_attempts}")

        rag_context = retrieve_context(question)
        generated_code = self.clean_code(self.generate_code(question, data_context, rag_context, complexity))
        logger.info(f"Generated code:\n{generated_code}")

        attempt = 1
        while attempt <= self.max_attempts:
            try:
                logger.info(f"Execution attempt {attempt} of {self.max_attempts}")
                result = self.execute_code(generated_code, file_path)
                logger.info("Execution successful")
                return result, attempt, self.model

            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {str(e)}")

                if attempt == self.max_attempts:
                    raise Exception(f"Python agent failed after {self.max_attempts} attempts: {str(e)}")

                generated_code = self.clean_code(self.fix_code(question, generated_code, str(e), data_context, rag_context, complexity))
                attempt += 1
