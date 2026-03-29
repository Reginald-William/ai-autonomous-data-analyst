import logging
import time
import pandas as pd
from datetime import datetime
from fastapi import HTTPException
from src.services.llm_service import MODEL_NAME
from src.agents.planner_agent import PlannerAgent
from src.agents.python_agent import PythonAgent
from src.agents.sql_agent import SQLAgent
from src.agents.chart_agent import ChartAgent
from src.utils.schemas import AnalysisResponse


logger = logging.getLogger(__name__)

planner = PlannerAgent()
python_agent = PythonAgent()
sql_agent = SQLAgent()
chart_agent = ChartAgent()

def analyse(question: str, file_path: str) -> AnalysisResponse:
    start_time = time.time()

    try:
        df = pd.read_csv(file_path)
        row_count = len(df)
        column_count = len(df.columns)
        file_name = file_path.split("/")[-1]
        logger.info(f"CSV loaded: {row_count} rows, {column_count} columns | File: {file_name}")

    except FileNotFoundError:
        logger.error(f"CSV file not found: {file_path}")
        raise HTTPException(status_code=404, detail=f"CSV file not found: {file_path}")

    plan = planner.run(question)
    agents = plan.get("agents", ["python"])
    task_type = plan.get("task_type", "analysis")
    reasoning = plan.get("reasoning", "")

    logger.info(f"Plan: task_type={task_type} | agents={agents}")

    result = None
    chart_path = None
    agents_used = []

    try:
        if "python" in agents:
            logger.info("Routing to Python agent")
            result = python_agent.run(question, file_path)
            agents_used.append("python")

        elif "sql" in agents:
            logger.info("Routing to SQL agent")
            result = sql_agent.run(question, file_path)
            agents_used.append("sql")

        if "chart" in agents and result is not None:
            logger.info("Routing to Chart agent")
            chart_path = chart_agent.run(question, result, file_path)
            agents_used.append("chart")

    except Exception as e:
        logger.error(f"Agent execution failed: {str(e)}")
        time_taken = f"{round(time.time() - start_time, 2)}s"
        return AnalysisResponse(
            question=question,
            result="Unable to answer your question at this time. Please try again or rephrase your question.",
            status="failed",
            attempts=1,
            time_taken=time_taken,
            model_used=MODEL_NAME,
            row_count=row_count,
            column_count=column_count,
            file_name=file_name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            agents_used=agents_used,
            task_type=task_type,
            reasoning=reasoning,
            chart_path=chart_path
        )

    time_taken = f"{round(time.time() - start_time, 2)}s"
    logger.info(f"Analysis complete | Time: {time_taken} | Agents: {agents_used}")

    return AnalysisResponse(
        question=question,
        result=result,
        status="success",
        attempts=1,
        time_taken=time_taken,
        model_used=MODEL_NAME,
        row_count=row_count,
        column_count=column_count,
        file_name=file_name,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        agents_used=agents_used,
        task_type=task_type,
        reasoning=reasoning,
        chart_path=chart_path
    )
