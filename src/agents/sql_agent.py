import logging
import sqlite3
from tabulate import tabulate
from src.services.llm_service import get_llm_client, MODEL_NAME
from src.services.database_service import load_csv_to_sqlite
from src.services.rag_service import retrieve_context

logger = logging.getLogger(__name__)

class SQLAgent:
    def __init__(self):
        self.client = get_llm_client()
        self.model = MODEL_NAME
        self.max_attempts = 3

    def generate_sql(self, question: str, db_info: dict, rag_context: str = "") -> str:
        schema = f"Table: {db_info['table_name']}\n"
        schema += f"Columns: {db_info['columns']}\n"
        schema += f"Row count: {db_info['row_count']}"

        prompt = f"""
        You are a SQL expert. You have access to a SQLite database with the following schema:

        {schema}

        Additional business context:
        {rag_context}

        The user is asking: {question}

        Write a SQLite SQL query to answer this question.
        Return only the SQL query, nothing else.
        Do not include any explanation or markdown.
        """

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a SQL expert who writes clean SQLite queries."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content.strip()

    def fix_sql(self, question: str, failed_sql: str, error: str, db_info: dict, rag_context: str = "") -> str:
        schema = f"Table: {db_info['table_name']}\n"
        schema += f"Columns: {db_info['columns']}\n"

        prompt = f"""
        You are a SQL expert. You have access to a SQLite database with the following schema:

        {schema}

        Additional business context:
        {rag_context}

        The user is asking: {question}

        You previously generated this SQL:
        {failed_sql}

        But it failed with this error:
        {error}

        Fix the SQL and return only the corrected query, nothing else.
        """

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a SQL expert who writes clean SQLite queries."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content.strip()

    def execute_sql(self, sql: str, db_path: str) -> str:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        conn.close()

        if not rows:
            return "Query executed successfully but returned no results"
        
        result = tabulate(rows, headers=columns, tablefmt="pretty")

        # Previously we formatted this way, but it was not clean
        # result = " | ".join(columns) + "\n"
        # result += "-" * 50 + "\n"
        # for row in rows:
        #     result += " | ".join(str(val) for val in row) + "\n"

        return result

    def clean_sql(self, sql: str) -> str:
      return sql.replace("```sql", "").replace("```", "").strip()
    
    def run(self, question: str, file_path: str) -> str:
        logger.info(f"SQL agent running for question: {question}")

        db_info = load_csv_to_sqlite(file_path)
        rag_context = retrieve_context(question)

        sql = self.generate_sql(question, db_info, rag_context)
        sql = self.clean_sql(sql)
        logger.info(f"Generated SQL:\n{sql}")

        attempt = 1
        while attempt <= self.max_attempts:
            try:
                logger.info(f"SQL execution attempt {attempt} of {self.max_attempts}")
                result = self.execute_sql(sql, db_info["db_path"])
                logger.info("SQL execution successful")
                return result

            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {str(e)}")

                if attempt == self.max_attempts:
                    raise Exception(f"SQL agent failed after {self.max_attempts} attempts: {str(e)}")

                sql = self.fix_sql(question, sql, str(e), db_info, rag_context)
                sql = self.clean_sql(sql)
                attempt += 1
