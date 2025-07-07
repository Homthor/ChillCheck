import psycopg2
from config import DB_CONFIG
from psycopg2.extras import DictCursor

def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    print("База Данных Подключена")
    return conn

# cursor = db_connection.cursor(cursor_factory=DictCursor)
#
# cursor.execute("SELECT * FROM USERS")
# result = cursor.fetchall()
# print(result)
#
# for users in result:
#     print(users['username'])
#
# for users in result:
#     print(users['email'])

# user = input('Введите пользователя ')
# login = input('Введите логин ')
# password_hash = input('Введите пароль ')

# sql = f"INSERT INTO users (username, email, password_hash) VALUES(%s,%s,%s)"
# cursor.execute(sql,(user, login, password_hash))

