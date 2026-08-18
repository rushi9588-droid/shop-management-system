import mysql.connector


connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="shop_management"
)

print("Database Connected Successfully")