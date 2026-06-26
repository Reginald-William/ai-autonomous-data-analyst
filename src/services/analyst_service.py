import logging
import time
import pandas as pd
from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException
from src.services.llm_service import DEFAULT_MODEL
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

def analyse(question: str, file_path: str, session_id: str = None, original_filename: str = None) -> AnalysisResponse:
    if session_id is None:
        session_id = str(uuid4())  # auto-generate for /ask backward compat
    start_time = time.time()

    try:
        df = pd.read_csv(file_path)
        row_count = len(df)
        column_count = len(df.columns)
        # Use original filename for display if provided (e.g. from upload), else extract from path
        file_name = original_filename if original_filename else file_path.split("/")[-1]
        logger.info(f"CSV loaded: {row_count} rows, {column_count} columns | File: {file_name}")

        if row_count == 0:
            logger.warning(f"CSV file has no data rows: {file_path}")
            raise HTTPException(status_code=400, detail="The CSV file contains no data rows. Please upload a file with at least one row of data.")

    except FileNotFoundError:
        logger.error(f"CSV file not found: {file_path}")
        raise HTTPException(status_code=404, detail=f"CSV file not found: {file_path}")

    plan = planner.run(question, row_count)
    agents = plan.get("agents", ["python"])
    task_type = plan.get("task_type", "analysis")
    complexity = plan.get("complexity", "medium")
    reasoning = plan.get("reasoning", "")

    logger.info(f"Plan: task_type={task_type} | complexity={complexity} | agents={agents}")

    # If the planner determined the question is out of scope, return early
    if "none" in agents:
        logger.info("Question out of scope — no agent dispatched")
        time_taken = f"{round(time.time() - start_time, 2)}s"
        return AnalysisResponse(
            question=question,
            result="This question cannot be answered from the provided data. Please ask a question related to the CSV file.",
            status="out_of_scope",
            attempts=0,
            time_taken=time_taken,
            model_used=DEFAULT_MODEL,
            row_count=row_count,
            column_count=column_count,
            file_name=file_name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            agents_used=[],
            task_type=task_type,
            reasoning=reasoning,
            chart_path=None,
            session_id=session_id
        )

    result = None
    chart_path = None
    agents_used = []
    model_used = DEFAULT_MODEL

    attempts = 1
    try:
        if "python" in agents:
            logger.info("Routing to Python agent")
            result, attempts, model_used = python_agent.run(question, file_path, complexity)
            agents_used.append("python")

        elif "sql" in agents:
            logger.info("Routing to SQL agent")
            result, attempts, model_used = sql_agent.run(question, file_path, complexity, session_id=session_id, original_filename=original_filename)
            agents_used.append("sql")

        if "chart" in agents and result is not None:
            logger.info("Routing to Chart agent")
            chart_path = chart_agent.run(question, result, file_path, complexity, session_id=session_id)
            agents_used.append("chart")

    except Exception as e:
        logger.error(f"Agent execution failed: {str(e)}")
        time_taken = f"{round(time.time() - start_time, 2)}s"
        return AnalysisResponse(
            question=question,
            result="Unable to answer your question at this time. Please try again or rephrase your question.",
            status="failed",
            attempts=attempts,
            time_taken=time_taken,
            model_used=model_used,
            row_count=row_count,
            column_count=column_count,
            file_name=file_name,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            agents_used=agents_used,
            task_type=task_type,
            reasoning=reasoning,
            chart_path=chart_path,
            session_id=session_id
        )

    time_taken = f"{round(time.time() - start_time, 2)}s"
    logger.info(f"Analysis complete | Time: {time_taken} | Agents: {agents_used}")

    return AnalysisResponse(
        question=question,
        result=result,
        status="success",
        attempts=attempts,
        time_taken=time_taken,
        model_used=model_used,
        row_count=row_count,
        column_count=column_count,
        file_name=file_name,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        agents_used=agents_used,
        task_type=task_type,
        reasoning=reasoning,
        chart_path=chart_path,
        session_id=session_id
    )
