import logging
from uuid import uuid4
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from src.services.llm_service import get_llm_client, get_model_for_complexity
from src.config import get_settings

logger = logging.getLogger(__name__)

class ChartAgent:
    def __init__(self, client=None, settings=None):
        self.client = client if client is not None else get_llm_client()
        self.model = get_model_for_complexity("medium")
        self.charts_dir = (settings if settings is not None else get_settings()).charts_dir

    def generate_chart_code(self, question: str, data: str, file_path: str, chart_path: str) -> str:
        df = pd.read_csv(file_path)
        csv_context = f"Columns: {list(df.columns)}\n"
        csv_context += f"Sample rows:\n{df.head(3).to_string()}"

        prompt = f"""
        You are a data visualization expert.

        The following data has already been computed and is the final result:
        {data}

        The user is asking: {question}

        Write Python code using matplotlib to create a clear and informative chart using ONLY the data provided above.
        Do not recompute or re-aggregate data from df.
        Parse the data provided and use it directly for the chart.
        Always add a title to the chart.
        Always label the x and y axes clearly.
        Always add value labels on top of each bar if it is a bar chart.
        Always use tight_layout() before saving.
        Save the chart to "{chart_path}" using plt.savefig("{chart_path}").
        Do not use plt.show().
        Return only the Python code, nothing else.
        Always write actual Python code, never answer directly.
        """

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a data visualization expert who writes clean matplotlib code."},
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content.strip()

    def clean_code(self, code: str) -> str:
        return code.replace("```python", "").replace("```", "").strip()

    def run(self, question: str, data: str, file_path: str, complexity: str = "medium", session_id: str = None) -> str:
        self.model = get_model_for_complexity(complexity)
        logger.info(f"Chart agent running for question: {question} | complexity={complexity} | model={self.model}")

        # Use session_id for the filename so concurrent requests don't overwrite each other
        chart_id = session_id if session_id else str(uuid4())
        chart_path = f"{self.charts_dir}/{chart_id}.png"

        chart_code = self.clean_code(self.generate_chart_code(question, data, file_path, chart_path))

        try:
            df = pd.read_csv(file_path)
            safe_environment = {"df": df, "plt": plt}
            exec(chart_code, safe_environment)
            logger.info(f"Chart saved to {chart_path}")
            return chart_path

        except Exception as e:
            logger.error(f"Chart generation failed: {str(e)}")
            raise Exception(f"Chart agent failed: {str(e)}")
