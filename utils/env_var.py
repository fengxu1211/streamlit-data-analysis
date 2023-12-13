import os
from dotenv import load_dotenv

load_dotenv()

RDS_MYSQL_USERNAME = os.getenv('RDS_MYSQL_USERNAME')
RDS_MYSQL_PASSWORD = os.getenv('RDS_MYSQL_PASSWORD')
RDS_MYSQL_HOST = os.getenv('RDS_MYSQL_HOST')
RDS_MYSQL_PORT = os.getenv('RDS_MYSQL_PORT')
RDS_MYSQL_DBNAME = os.getenv('RDS_MYSQL_DBNAME')

RDS_PQ_SCHEMA = os.getenv('RDS_PQ_SCHEMA')