import os
import mysql.connector
import psycopg2
from psycopg2.extras import RealDictCursor

connection = mysql.connector.connect(
    host=os.getenv("DB_HOST", "dpg-da2q8uj7uimc73b70vg0-a"),
    user=os.getenv("DB_USER", "shop_management_kxqv_user"),
    password=os.getenv("DB_PASSWORD", "cC3I6Iy9XiEvffVn28NSP3knYFhFgFdz"),
    database=os.getenv("DB_NAME", "shop_management_kxqv"),
    port=int(os.getenv("DB_PORT", 5432))
)
