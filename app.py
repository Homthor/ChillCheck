from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from jinja2 import Environment, FileSystemLoader
from db import get_connection
from utils import hash_password, check_password
from auth import get_logged_in_user

env = Environment(loader=FileSystemLoader('templates'))


class MyHandler(BaseHTTPRequestHandler):

    def render_template(self, template_name, context=None):
        context = context or {}
        template = env.get_template(template_name)
        html = template.render(context)
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())

    def do_GET(self):
        if self.path == '/register':
            self.render_template('register.html')

        elif self.path == '/login':
            self.render_template('login.html')

        elif self.path == '/forgot-password':
            self.render_template('forgot_password.html')  # макет пока

        elif self.path == '/create_house':

            user_id = get_logged_in_user(self.headers)

            if not user_id:
                self.send_response(302)

                self.send_header('Location', '/login')

                self.end_headers()

                return

            self.render_template('create_house.html')

        elif self.path == '/join_house':

            user_id = get_logged_in_user(self.headers)

            if not user_id:
                self.send_response(302)

                self.send_header('Location', '/login')
                self.end_headers()

                return

            self.render_template('join_house.html')

        elif self.path == '/logout':
            self.send_response(302)
            self.send_header('Location', '/login')
            # удаляем cookie (делаем истёкшей)
            self.send_header('Set-Cookie', 'user_id=; Path=/; Max-Age=0')
            self.end_headers()

        elif self.path == '/create_house':
            user_id = get_logged_in_user(self.headers)
            if not user_id:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return

            self.render_template('create_house.html')

        elif self.path == '/dashboard':
            user_id = get_logged_in_user(self.headers)
            if not user_id:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return

            try:
                conn = get_connection()
                cur = conn.cursor()

                # Получаем имя пользователя
                cur.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
                username = cur.fetchone()[0]

                # Получаем информацию о доме
                cur.execute("""
                    SELECT h.house_id, h.house_name, h.join_code
                    FROM house_users hu
                    JOIN houses h ON hu.house_id = h.house_id
                    WHERE hu.user_id = %s
                """, (user_id,))
                house = cur.fetchone()

                context = {
                    'username': username
                }

                if house:
                    house_id, house_name, join_code = house
                    context.update({
                        'house_name': house_name,
                        'join_code': join_code
                    })

                    # Получаем inventory
                    cur.execute("""
                        SELECT bp.product_name, hi.quantity
                        FROM house_inventory hi
                        JOIN base_products bp ON hi.product_id = bp.product_id
                        WHERE hi.house_id = %s
                    """, (house_id,))
                    inventory = cur.fetchall()
                    context['inventory'] = inventory

                    # Получаем список покупок
                    cur.execute("""
                        SELECT bp.product_name, sl.quantity
                        FROM shopping_list sl
                        JOIN base_products bp ON sl.product_id = bp.product_id
                        WHERE sl.house_id = %s
                    """, (house_id,))
                    shopping_list = cur.fetchall()
                    context['shopping_list'] = shopping_list

                cur.close()
                conn.close()

                self.render_template('dashboard.html', context)

            except Exception as e:
                self.render_template('dashboard.html', {'error': str(e)})

        elif self.path == '/':
            user_id = get_logged_in_user(self.headers)
            if user_id:
                self.send_response(302)
                self.send_header('Location', '/dashboard')
                self.end_headers()
            else:
                self.render_template('index.html')

        else:
            self.send_error(404, 'Page Not Found')

    def do_POST(self):
        if self.path == '/register':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode()
            data = parse_qs(post_data)

            username = data.get('username', [''])[0]
            email = data.get('email', [''])[0]
            password = data.get('password', [''])[0]
            password_repeat = data.get('password_repeat', [''])[0]

            if not username or not email or not password:
                self.render_template('register.html', {'error': 'Все поля обязательны'})
                return

            if password != password_repeat:
                self.render_template('register.html', {'error': 'Пароли не совпадают'})
                return

            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO users (username, email, password_hash)
                    VALUES (%s, %s, %s)
                """, (username, email, hash_password(password)))
                conn.commit()
                cur.close()
                conn.close()
                self.send_response(302)
                self.send_header('Location', '/login')  # будущая страница
                self.end_headers()
            except Exception as e:
                error_msg = str(e)
                if "unique" in error_msg.lower():
                    error_msg = "Пользователь с таким именем или email уже существует"
                self.render_template('register.html', {'error': error_msg})

        elif self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode()
            data = parse_qs(post_data)

            email = data.get('email', [''])[0]
            password = data.get('password', [''])[0]

            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT user_id, password_hash FROM users WHERE email = %s", (email,))
                user = cur.fetchone()
                cur.close()
                conn.close()

                if user and check_password(password, user[1]):
                    self.send_response(302)
                    self.send_header('Location', '/dashboard')
                    self.send_header('Set-Cookie', f'user_id={user[0]}; Path=/')
                    self.end_headers()
                else:
                    self.render_template('login.html', {'error': 'Неверный email или пароль'})

            except Exception as e:
                self.render_template('login.html', {'error': f'Ошибка входа: {str(e)}'})

        elif self.path == '/create_house':
            user_id = get_logged_in_user(self.headers)
            if not user_id:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return

            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode()
            data = parse_qs(post_data)

            house_name = data.get('house_name', [''])[0].strip()
            if not house_name:
                self.render_template('create_house.html', {'error': 'Название дома обязательно'})
                return

            from utils import generate_join_code
            join_code = generate_join_code()

            try:
                conn = get_connection()
                cur = conn.cursor()

                # Проверка: пользователь уже состоит в доме?
                cur.execute("SELECT house_id FROM house_users WHERE user_id = %s", (user_id,))
                if cur.fetchone():
                    self.render_template('create_house.html', {'error': 'Вы уже состоите в доме'})
                    return

                # Создание дома
                cur.execute("""
                    INSERT INTO houses (house_name, join_code)
                    VALUES (%s, %s)
                    RETURNING house_id
                """, (house_name, join_code))
                house_id = cur.fetchone()[0]

                # Привязка пользователя к дому
                cur.execute("""
                    INSERT INTO house_users (user_id, house_id)
                    VALUES (%s, %s)
                """, (user_id, house_id))

                conn.commit()
                cur.close()
                conn.close()

                self.send_response(302)
                self.send_header('Location', '/dashboard')
                self.end_headers()

            except Exception as e:
                self.render_template('create_house.html', {'error': f'Ошибка: {str(e)}'})

        elif self.path == '/join_house':
            user_id = get_logged_in_user(self.headers)
            if not user_id:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return

            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode()
            data = parse_qs(post_data)

            join_code = data.get('join_code', [''])[0].strip().upper()

            if not join_code:
                self.render_template('join_house.html', {'error': 'Введите код дома'})
                return

            try:
                conn = get_connection()
                cur = conn.cursor()

                # Проверка: уже состоит в доме?
                cur.execute("SELECT 1 FROM house_users WHERE user_id = %s", (user_id,))
                if cur.fetchone():
                    self.render_template('join_house.html', {'error': 'Вы уже состоите в доме'})
                    return

                # Проверка: существует ли дом с таким кодом
                cur.execute("SELECT house_id FROM houses WHERE join_code = %s", (join_code,))
                row = cur.fetchone()
                if not row:
                    self.render_template('join_house.html', {'error': 'Неверный код'})
                    return

                house_id = row[0]

                # Добавляем в связующую таблицу
                cur.execute("INSERT INTO house_users (user_id, house_id) VALUES (%s, %s)", (user_id, house_id))
                conn.commit()
                cur.close()
                conn.close()

                self.send_response(302)
                self.send_header('Location', '/dashboard')
                self.end_headers()

            except Exception as e:
                self.render_template('join_house.html', {'error': f'Ошибка: {str(e)}'})
        #   Добавление (Орбаботка ниже)
        elif self.path == '/add_to_inventory':
            self.handle_add_product(table='house_inventory')

        elif self.path == '/add_to_shopping_list':
            self.handle_add_product(table='shopping_list')
        # Удаление
        elif self.path == '/remove_from_inventory':
            self.handle_remove_product(table='house_inventory')

        elif self.path == '/remove_from_shopping_list':
            self.handle_remove_product(table='shopping_list')


    def handle_add_product(self, table):
        user_id = get_logged_in_user(self.headers)
        if not user_id:
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode()
        data = parse_qs(post_data)

        product_name = data.get('product_name', [''])[0].strip()
        quantity = data.get('quantity', [''])[0]

        if not product_name or not quantity:
            self.send_response(302)
            self.send_header('Location', '/dashboard')
            self.end_headers()
            return

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Получаем house_id
            cur.execute("SELECT house_id FROM house_users WHERE user_id = %s", (user_id,))
            result = cur.fetchone()
            if not result:
                raise Exception("Вы не привязаны к дому.")
            house_id = result[0]

            # Проверяем, есть ли такой продукт в базе
            cur.execute("SELECT product_id FROM base_products WHERE product_name = %s", (product_name,))
            row = cur.fetchone()
            if row:
                product_id = row[0]
            else:
                # Добавляем в base_products
                cur.execute("INSERT INTO base_products (product_name) VALUES (%s) RETURNING product_id",
                            (product_name,))
                product_id = cur.fetchone()[0]

            # Добавляем/обновляем в соответствующей таблице
            cur.execute(f"""
                INSERT INTO {table} (house_id, product_id, quantity)
                VALUES (%s, %s, %s)
                ON CONFLICT (house_id, product_id)
                DO UPDATE SET quantity = {table}.quantity + EXCLUDED.quantity
            """, (house_id, product_id, quantity))

            conn.commit()
            cur.close()
            conn.close()

            self.send_response(302)
            self.send_header('Location', '/dashboard')
            self.end_headers()

        except Exception as e:
            self.render_template('dashboard.html', {'error': str(e)})

    def handle_remove_product(self, table):
        user_id = get_logged_in_user(self.headers)
        if not user_id:
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode()
        data = parse_qs(post_data)
        product_name = data.get('product_name', [''])[0].strip()

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Получаем house_id
            cur.execute("SELECT house_id FROM house_users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                raise Exception("Пользователь не состоит в доме")
            house_id = row[0]

            # Получаем product_id
            cur.execute("SELECT product_id FROM base_products WHERE product_name = %s", (product_name,))
            row = cur.fetchone()
            if not row:
                raise Exception("Продукт не найден")
            product_id = row[0]

            # Удаляем продукт из нужной таблицы
            cur.execute(f"DELETE FROM {table} WHERE house_id = %s AND product_id = %s", (house_id, product_id))

            conn.commit()
            cur.close()
            conn.close()

            self.send_response(302)
            self.send_header('Location', '/dashboard')
            self.end_headers()

        except Exception as e:
            self.render_template('dashboard.html', {'error': str(e)})


def run():
    server_address = ('localhost', 8000)
    httpd = HTTPServer(server_address, MyHandler)
    print("Server running at http://localhost:8000")
    httpd.serve_forever()


if __name__ == '__main__':
    run()
