import sqlite3
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

def load_csv_to_sqlite(file_path: str) -> dict:
    try:
        # Derive table name from filename
        file_name = os.path.basename(file_path)
        table_name = os.path.splitext(file_name)[0]
        
        # Define database path
        db_path = f"data/{table_name}.db"
        
        # Load CSV into dataframe
        df = pd.read_csv(file_path)
        
        # Connect to SQLite and load dataframe as table
        conn = sqlite3.connect(db_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.close()
        
        logger.info(f"CSV loaded into SQLite: {db_path} | Table: {table_name}")
        
        return {
            "db_path": db_path,
            "table_name": table_name,
            "columns": list(df.columns),
            "row_count": df.shape[0],
            "column_count": df.shape[1]
        }
    
    except Exception as e:
        logger.error(f"Failed to load CSV to SQLite: {str(e)}")
        raise Exception(f"Database error: {str(e)}")
