# import os
# import mysql.connector

# connection = mysql.connector.connect(
#     host=os.getenv("DB_HOST", "dpg-da2q8uj7uimc73b70vg0-a"),
#     user=os.getenv("DB_USER", "shop_management_kxqv_user"),
#     password=os.getenv("DB_PASSWORD", "cC3I6Iy9XiEvffVn28NSP3knYFhFgFdz"),
#     database=os.getenv("DB_NAME", "shop_management_kxqv"),
#     port=int(os.getenv("DB_PORT", 5432))
# )
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    connection = psycopg2.connect(
        host=os.getenv("DB_HOST","dpg-da2q8uj7uimc73b70vg0-a"),
        port=os.getenv("DB_PORT", 5432),
        database=os.getenv("DB_NAME", "shop_management_kxqv"),
        user=os.getenv("DB_USER", "shop_management_kxqv_user"),
        password=os.getenv("DB_PASSWORD", "cC3I6Iy9XiEvffVn28NSP3knYFhFgFdz")
    )
    return connection