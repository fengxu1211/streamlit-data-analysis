import sqlalchemy as db
from sqlalchemy import text
from utils.env_var import RDS_MYSQL_HOST, RDS_MYSQL_PORT, RDS_MYSQL_USERNAME, RDS_MYSQL_PASSWORD, RDS_MYSQL_DBNAME
import logging

logger = logging.getLogger(__name__)


def query_from_database(db_url: str, query):
    """
    Query the database
    """
    try:
        engine = db.create_engine(db_url.format(
            RDS_MYSQL_HOST=RDS_MYSQL_HOST,
            RDS_MYSQL_PORT=RDS_MYSQL_PORT,
            RDS_MYSQL_USERNAME=RDS_MYSQL_USERNAME,
            RDS_MYSQL_PASSWORD=RDS_MYSQL_PASSWORD,
            RDS_MYSQL_DBNAME=RDS_MYSQL_DBNAME,
        ))
        connection = engine.connect()
        logger.info(f'{query=}')
        cursor = connection.execute(text(query))
        results = cursor.fetchall()
        columns = list(cursor.keys())
    except ValueError as e:
        logger.exception(e)
        return {"status": "error", "message": str(e)}
    return {
        "status": "ok",
        "data": str(results),
        "query": query,
        "columns": columns
    }