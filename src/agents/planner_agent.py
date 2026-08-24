import logging
import json
from src.services.llm_service import get_llm_client, DEFAULT_MODEL, MODEL_ROUTING
from src.services.rag_service import retrieve_context

logger = logging.getLogger(__name__)

class PlannerAgent:
    def __init__(self):
        self.client = get_llm_client()
        self.model = DEFAULT_MODEL
        self.complexity_model = MODEL_ROUTING["low"]  # gpt-oss-20b — fast, cheap, focused

    # Minimum rows required to justify the high complexity model
    HIGH_COMPLEXITY_ROW_THRESHOLD = 500

    def _classify_complexity(self, question: str, task_type: str, row_count: int) -> str:
        """Dedicated call whose only job is to classify task complexity."""
        prompt = f"""
        You are a task complexity classifier. Classify the complexity of this data analysis question as low, medium, or high.

        Definitions:
        - low: single metric, one operation, one column, answer is a single value (e.g. total revenue, row count, max price)
        - medium: grouping, filtering, sorting, aggregation across categories, or any visualization (e.g. revenue by region, top 5 products, bar chart)
        - high: two or more separate computations combined, trend over time, correlation, or comparing performance across multiple dimensions (e.g. which region is growing fastest, revenue trend over time, correlation between product and region)

        Task type already determined: {task_type}
        Question: {question}

        Respond with a single JSON object:
        {{"complexity": "low|medium|high"}}
        """

        response = self.client.chat.completions.create(
            model=self.complexity_model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": "You are a classifier that responds only with a single JSON object."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(result)
        complexity = parsed.get("complexity", "medium")

        # Downgrade high → medium for small datasets — not enough data to justify heavier model
        if complexity == "high" and row_count < self.HIGH_COMPLEXITY_ROW_THRESHOLD:
            logger.info(f"Downgrading complexity high → medium (row_count={row_count} < threshold={self.HIGH_COMPLEXITY_ROW_THRESHOLD})")
            complexity = "medium"

        logger.info(f"Complexity classified as: {complexity}")
        return complexity

    def run(self, question: str, row_count: int = 0) -> dict:
        logger.info(f"Planner agent analyzing question: {question}")

        rag_context = retrieve_context(question)

        routing_prompt = f"""
        You are a planner for a data analysis system.
        You have these specialized agents available:
        - python: for data analysis, calculations, and computations using pandas
        - sql: for structured queries, filtering, and retrieving specific records
        - chart: for generating visual charts and graphs (always used after python or sql)
        - none: when the question cannot be answered from the CSV data at all

        Routing rules:
        - If the question mentions any of these words: chart, graph, plot, visualize, visualization, show me, bar, line, pie, histogram, scatter, horizontal — always include "chart" in agents
        - If the question asks to retrieve specific records or filter data — use "sql"
        - If the question asks for calculations, totals, averages, comparisons — use "python"
        - If the question needs both computation and visualization — use ["python", "chart"]
        - If the question is about general world knowledge, external facts, or topics completely unrelated to the data (e.g. weather, geography, people, news) — use "none"

        Additional context:
        {rag_context}

        Based on the user question, decide which agents to use and in what order.

        User question: {question}

        Respond ONLY with a JSON object in this exact format:
        {{
            "task_type": "analysis|query|visualization|comparison|out_of_scope",
            "agents": ["python"] or ["sql"] or ["python", "chart"] or ["sql", "chart"] or ["none"],
            "reasoning": "brief explanation of why you chose these agents"
        }}
        """

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a planner that responds only in valid JSON."},
                {"role": "user", "content": routing_prompt}
            ]
        )

        result = response.choices[0].message.content
        result = result.replace("```json", "").replace("```", "").strip()  # Clean up the JSON response

        plan = json.loads(result)  # Parse string to Python dict
        logger.info(f"Routing plan: {plan}")

        # Call 2 — dedicated complexity classifier on the fast 8B model
        complexity = self._classify_complexity(question, plan.get("task_type", "analysis"), row_count)
        plan["complexity"] = complexity

        logger.info(f"Final plan: task_type={plan.get('task_type')} | complexity={complexity} | agents={plan.get('agents')}")

        return plan
