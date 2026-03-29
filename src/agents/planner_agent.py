import logging
import json
from src.services.llm_service import get_llm_client, MODEL_NAME
from src.services.rag_service import retrieve_context

logger = logging.getLogger(__name__)

class PlannerAgent:
    def __init__(self):
        self.client = get_llm_client()
        self.model = MODEL_NAME
    
    def run(self, question: str) -> dict:
        logger.info(f"Planner agent analyzing question: {question}")
        
        rag_context = retrieve_context(question)
        
        prompt = f"""
        You are a planner for a data analysis system. 
        You have these specialized agents available:
        - python: for data analysis, calculations, and computations using pandas
        - sql: for structured queries, filtering, and retrieving specific records
        - chart: for generating visual charts and graphs (always used after python or sql)
        
        Routing rules:
        - If the question mentions any of these words: chart, graph, plot, visualize, visualization, show me, bar, line, pie, histogram, scatter, horizontal — always include "chart" in agents
        - If the question asks to retrieve specific records or filter data — use "sql"
        - If the question asks for calculations, totals, averages, comparisons — use "python"
        - If the question needs both computation and visualization — use ["python", "chart"]

        Additional context:
        {rag_context}
        
        Based on the user question, decide which agents to use and in what order.
        
        User question: {question}
        
        Respond ONLY with a JSON object in this exact format:
        {{
            "task_type": "analysis|query|visualization|comparison",
            "agents": ["python"] or ["sql"] or ["python", "chart"] or ["sql", "chart"],
            "reasoning": "brief explanation of why you chose these agents"
        }}
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a planner that responds only in valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        
        result = response.choices[0].message.content
        result = result.replace("```json", "").replace("```", "").strip()  # Clean up the JSON response
        
        plan = json.loads(result)  # Parse string to Python dict
        logger.info(f"Plan created: {plan}")
        
        return plan
