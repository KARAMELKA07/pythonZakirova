from flask import Flask, render_template, url_for, request, redirect, session
import psycopg2
import builtins
import bcrypt

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@app.context_processor
def inject_enumerate():
    return dict(enumerate=builtins.enumerate)


conn_params = {
    "host": "localhost",
    "port": "5432",
    "database": "DS",
    "user": "postgres",
    "password": "Mirra2019"
}


def get_db_connection():
    conn = psycopg2.connect(**conn_params)
    return conn


def hash_password(password, stored_password_hash=None):
    if stored_password_hash:
        salt = stored_password_hash[:29].encode('utf-8')
    else:
        salt = bcrypt.gensalt()

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')


roles = ['пользователь', 'аналитик', 'менеджер', 'администратор']

@app.route('/', methods=['GET', 'POST'])
def login_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        c = conn.cursor()

        if role == 'пользователь':
            c.execute("SELECT password_hash, id_client FROM clients WHERE login = %s", (username,))
            result = c.fetchone()

            if result:
                stored_password_hash, user_id = result
                hashed_password = hash_password(password, stored_password_hash)

                if hashed_password == stored_password_hash:
                    print('Успешный вход')
                    session['user_id'] = user_id
                    return redirect(url_for('user_page', user_id=user_id))
                else:
                    print('Неверный логин, пароль или роль')
            else:
                print('Неверный логин, пароль или роль')
        else:
            c.execute("SELECT password_hash, name_role, id_staff FROM staff WHERE login = %s", (username,))
            result = c.fetchone()

            if result:
                stored_password_hash, stored_role, staff_id = result
                hashed_password = hash_password(password, stored_password_hash)
                if hashed_password == stored_password_hash and role == stored_role:
                    print('Успешный вход')

                    if role == 'аналитик':
                        session['staff_id'] = staff_id
                        return redirect(url_for('analyst_page', staff_id=staff_id))
                    elif role == 'менеджер':
                        session['staff_id'] = staff_id
                        return redirect(url_for('manager_page', staff_id=staff_id))
                    else:
                        session['staff_id'] = staff_id
                        return redirect(url_for('admin_page', staff_id=staff_id))
                else:
                    print('Неверный логин, пароль или роль')
            else:
                print('Неверный логин, пароль или роль')
    return render_template('login_register.html', roles=roles)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form['full_name']
        phone_number = request.form['phone_number']

        if password != confirm_password:
            return "Passwords do not match"

        hashed_password = hash_password(password)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO clients (full_name, phone_number, login, password, password_hash) VALUES (%s, %s, %s, %s, %s)", (full_name, phone_number, username, password, hashed_password))
        conn.commit()
        cur.close()
        conn.close()

        return "Вы зарегистрированы"

    return render_template('register.html')


@app.route('/user/<int:user_id>', methods=['GET', 'POST'])
def user_page(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login_register'))

    user_id = session['user_id']

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id_device, name_device, cost FROM equipment")
    rows_second_table = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]

    cur.execute("SELECT id_service, name_service, cost FROM service")
    rows = cur.fetchall()
    column_names_second_table = [desc[0] for desc in cur.description]

    cur.execute("SELECT full_name, status, bonus FROM clients WHERE id_client = %s", (user_id,))
    user_data = cur.fetchone()
    user_full_name, user_status, bonus = user_data

    cur.close()
    conn.close()

    if request.method == 'GET':
        return render_template("request.html", data=rows, column_names=column_names, data_second_table=rows_second_table, column_names_second_table=column_names_second_table, user_full_name=user_full_name, user_status=user_status, bonus=bonus)

    if request.method == 'POST':
        selected_services = request.form.getlist('services[]')
        selected_equipment = request.form.getlist('equipment[]')

        filtered_services = [','.join(map(str, rows[int(index)])) for index in selected_services]
        filtered_equipment = [','.join(map(str, rows_second_table[int(index)])) for index in selected_equipment]

        return redirect(url_for('order', services=filtered_services, equipment=filtered_equipment, bonus=bonus))


@app.route('/order', methods=['GET', 'POST'])
def order():
    services = [i.split(',') for i in request.args.getlist('services')]
    equipment = [i.split(',') for i in request.args.getlist('equipment')]
    bonus = request.args.get('bonus')
    if request.method == 'POST':
        selected_services = request.form.getlist('services[]')
        selected_equipment = request.form.getlist('equipment[]')
        service_rental_period = request.form.getlist('service_rental_period[]')
        equipment_rental_period = request.form.getlist('equipment_rental_period[]')
        return redirect(url_for('submit_order', services=selected_services, equipment=selected_equipment, bonus=bonus, service_rental_period=service_rental_period, equipment_rental_period=equipment_rental_period))
    return render_template('order.html', services=services, equipment=equipment, bonus=bonus)


@app.route('/submit_order', methods=['GET', 'POST'])
def submit_order():
    if 'user_id' not in session:
        return redirect(url_for('login_register'))

    user_id = session['user_id']
    selected_services = request.args.getlist('services')
    selected_equipment = request.args.getlist('equipment')
    service_rental_period = request.args.getlist('service_rental_period')
    equipment_rental_period = request.args.getlist('equipment_rental_period')
    
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT bonus FROM clients WHERE id_client = %s", (user_id,))
    bonus = cur.fetchone()[0]

    cur.execute("SELECT id_service, name_service, cost FROM service")
    rows = cur.fetchall()
    services_data = []
    for i, index in enumerate(selected_services):
        service_index = int(index) - 1
        service_id = rows[service_index][0]
        service_name = rows[service_index][1]
        base_cost = rows[service_index][2]
        rental_period = int(service_rental_period[i])
        final_cost = int(base_cost * rental_period * (100 - bonus) / 100)
        services_data.append((service_id, service_name, final_cost))

    cur.execute("SELECT id_device, name_device, cost FROM equipment")
    rows_second_table = cur.fetchall()
    equipment_data = []
    for i, index in enumerate(selected_equipment):
        equipment_index = int(index) - 1
        equipment_id = rows_second_table[equipment_index][0]
        equipment_name = rows_second_table[equipment_index][1]
        base_cost = rows_second_table[equipment_index][2]
        rental_period = int(equipment_rental_period[i])
        final_cost = int(base_cost * rental_period * (100 - bonus) / 100)
        equipment_data.append((equipment_id, equipment_name, final_cost))

    for service_id, service_name, final_cost in services_data:
        cur.execute("INSERT INTO requests (id_client, finalcost, id_service) VALUES (%s, %s, %s)", (user_id, final_cost, service_id))

    for equipment_id, equipment_name, final_cost in equipment_data:
        cur.execute("INSERT INTO requests (id_client, finalcost, id_device) VALUES (%s, %s, %s)", (user_id, final_cost, equipment_id))
   
    conn.commit()
    cur.close()
    conn.close()

    return 'Order submitted successfully!'


@app.route('/analyst/<int:staff_id>', methods=['GET', 'POST'])
def analyst_page(staff_id):
    if 'staff_id' not in session:
        return redirect(url_for('login_register')) 
    
    staff_id = session['staff_id']
    
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT full_name FROM staff WHERE id_staff = %s", (staff_id,))
    analyst_data = cur.fetchone()
    analyst_name = analyst_data[0]

    cur.execute("SELECT id_client, full_name, status, money_spent, bonus, phone_number, id_staff FROM clients")
    clients_data = cur.fetchall()

    if request.method == 'POST':
        report_type = request.form['report_type']

        if report_type == 'total_income':
            cur.execute('SELECT total_income FROM get_total_income()')
            data = cur.fetchone()[0]
            with open('total_income_report.csv', 'w') as f:
                f.write('Общий доход по ЦОДам:\n')
                f.write(f"{data}\n")

        elif report_type == 'centre_income':
            cur.execute("SELECT name_cod, centre_income FROM get_centre_income()")
            data = cur.fetchall()
            with open('centre_income_report.csv', 'w') as f:
                f.write('Центр, Доход центра\n')
                for row in data:
                    f.write(f"{row[0]}, {row[1]}\n")

        elif report_type == 'top_income_employees':
            cur.execute('SELECT * FROM get_top_income_employees()')
            data = cur.fetchall()
            with open('top_income_employees_report.csv', 'w') as f:
                f.write('ФИО сотрудника, Услуга, Оборудование, Доход\n')
                for row in data:
                    if row[1] is not None:
                        f.write(f"{row[0]}, {row[1]}, '', {row[3]}\n")
                    else:
                        f.write(f"{row[0]}, '', {row[2]}, {row[3]}\n")

        elif report_type == 'count_clients_by_status':
            cur.execute("SELECT * FROM count_clients_by_status()")
            data = cur.fetchall()
            with open('count_clients_by_status.csv', 'w') as f:
                f.write('Статус, Количество клиентов\n')
                for row in data:
                    f.write(f"{row[0]}, {row[1]}\n")

        conn.commit()

        return "Отчет сформирован успешно!"
    
    cur.close()
    conn.close()

    return render_template("analyst.html", analyst_name=analyst_name, clients=clients_data)


@app.route('/manager/<int:staff_id>', methods=['GET', 'POST'])
def manager_page(staff_id):
    if 'staff_id' not in session:
        return redirect(url_for('login_register'))
    
    staff_id = session['staff_id']
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT full_name FROM staff WHERE id_staff = %s", (staff_id,))
    manager_data = cur.fetchone()
    manager_name = manager_data[0]
    
    cur.execute("SELECT id_client, full_name, status, money_spent, bonus, phone_number, id_staff FROM clients WHERE id_staff = %s", (staff_id,))
    clients_column_names = [desc[0] for desc in cur.description]
    clients_data = cur.fetchall()

    cur.execute("SELECT * FROM requests WHERE id_staff = %s", (staff_id,))
    requests_column_names = [desc[0] for desc in cur.description]
    requests_data = cur.fetchall()

    cur.execute("SELECT id_client, full_name, status, money_spent, bonus, phone_number, id_staff FROM clients")
    clients_data_search = cur.fetchall()

    if request.method == 'POST':
        if 'edit_client' in request.form:
            client_id = request.form['client_id']
            full_name = request.form['full_name']
            status = request.form['status']
            money_spent = request.form['money_spent']
            bonus = request.form['bonus']
            phone_number = request.form['phone_number']
            id_staff = request.form['id_staff']

            cur.execute("""
                UPDATE clients 
                SET full_name = %s, status = %s, money_spent = %s, bonus = %s, phone_number = %s, id_staff = %s 
                WHERE id_client = %s
            """, (full_name, status, money_spent, bonus, phone_number, id_staff, client_id))
        elif 'delete_client' in request.form:
            client_id = request.form['client_id']
            cur.execute("DELETE FROM clients WHERE id_client = %s", (client_id,))
        elif 'edit_request' in request.form:
            request_id = request.form['request_id']
            id_client = request.form['id_client']
            finalcost = request.form['finalcost']
            request_staff_id = request.form['request_staff_id']
            id_device = request.form['id_device']
            id_service = request.form['id_service']
            cur.execute("""
                UPDATE requests 
                SET id_client = %s, finalcost = %s, id_staff = %s, id_device = %s, id_service = %s 
                WHERE id_request = %s
            """, (id_client, finalcost, request_staff_id, id_device, id_service, request_id))
        elif 'delete_request' in request.form:
            request_id = request.form['request_id']
            cur.execute("DELETE FROM requests WHERE id_request = %s", (request_id,))
        
        conn.commit()
        return redirect(url_for('manager_page', staff_id=staff_id))
    
    cur.close()
    conn.close()
    
    return render_template("manager.html", manager_name=manager_name, clients=clients_data_search, clients_data=clients_data, clients_column_names=clients_column_names, requests_data=requests_data, requests_column_names=requests_column_names)


def get_table_data(table_name):
    conn = get_db_connection()
    cur = conn.cursor()
    if table_name == 'clients':
        cur.execute(f"SELECT id_client, full_name, status, money_spent, bonus, phone_number, id_staff FROM {table_name}")
    elif table_name == 'staff':
        cur.execute(f"SELECT id_staff, full_name, post, salary, email, phone_number, experience, name_cod, brief_information, name_role FROM {table_name}")
    else:
        cur.execute(f"SELECT * FROM {table_name}")
    column_names = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows, column_names


@app.route('/show_table/<table_name>')
def show_table(table_name):
    table_data, column_names = get_table_data(table_name)
    return render_template('table_for_analyst.html', table_name=table_name, table_data=table_data, column_names=column_names)


@app.route('/admin/<int:staff_id>', methods=['GET', 'POST'])
def admin_page(staff_id):
    if 'staff_id' not in session:
        return redirect(url_for('login_register'))
    
    staff_id = session['staff_id']

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id_client, full_name, status, money_spent, bonus, phone_number, id_staff FROM clients")
    clients_data_search = cur.fetchall()

    cur.execute("SELECT full_name, name_cod FROM staff WHERE id_staff = %s", (staff_id,))
    admin_data = cur.fetchone()
    admin_name, admin_name_cod = admin_data

    if request.method == 'POST':
        report_type = request.form['report_type']

        if report_type == 'staff_report':
            cur.execute("SELECT * FROM get_staff_report(%s)", (admin_name_cod,))
            data = cur.fetchall()
            with open('staff_report.csv', 'w') as f:
                f.write('ФИО, Должность, ЦОД, Количество заявок, Доход\n')
                for row in data:
                    if row[3] != 0:
                        f.write(f"{row[0]}, {row[1]}, {row[2]}, {row[3]}, {row[4]}\n")

        elif report_type == 'equipment_report':
            center_code = ''.join(filter(str.isdigit, admin_name_cod))
            center_name = 'ЦОД ' + center_code
            cur.execute("SELECT * FROM get_device_report(%s)", (center_name,))
            data = cur.fetchall()
            with open('device_report.csv', 'w') as f:
                f.write('Название оборудования, Цена аренды на 1 месяц, ЦОД, Количество заказов, Доход\n')
                for row in data:
                    if row[3] != 0:
                        f.write(f"{row[0]}, {row[1]}, {row[2]}, {row[3]}, {row[4]}\n")
                    else:
                        f.write(f"НЕТ заказов по аренде {row[0]} в {center_name}\n")
        conn.commit()

        return "Отчет сформирован успешно!"

    cur.close()
    conn.close()
    return render_template('admin.html', clients=clients_data_search, admin_name=admin_name)


@app.route('/edit/<string:table_name>', methods=['GET', 'POST'])
def edit_table(table_name):
    if 'staff_id' not in session:
        return redirect(url_for('login_register'))
    
    staff_id = session['staff_id']

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        action = request.form['action']
        if action == 'add':
            columns = ', '.join([col for col in request.form.keys() if col not in ['action', 'id', 'primary_key_column']])
            values = tuple(request.form.get(col) for col in request.form.keys() if col not in ['action', 'id', 'primary_key_column'])
            placeholders = ', '.join(['%s'] * len(values))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            cur.execute(query, values)
        elif action == 'edit':
            primary_key_column = request.form['primary_key_column']
            columns = [col for col in request.form.keys() if col not in ['action', 'id', 'primary_key_column']]
            set_clause = ', '.join([f"{col} = %s" for col in columns])
            values = tuple(request.form.get(col) for col in columns)
            row_id = request.form['id']
            query = f"UPDATE {table_name} SET {set_clause} WHERE {primary_key_column} = %s"
            cur.execute(query, values + (row_id,))
        elif action == 'delete':
            primary_key_column = request.form['primary_key_column']
            row_id = request.form['id']
            query = f"DELETE FROM {table_name} WHERE {primary_key_column} = %s"
            cur.execute(query, (row_id,))
        conn.commit()

    cur.execute(f"SELECT * FROM {table_name}")
    table_data = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]
    primary_key_column = column_names[0]  

    cur.close()
    conn.close()
    return render_template('edit_table.html', some_staff_id=staff_id, table_name=table_name, table_data=table_data, column_names=column_names, primary_key_column=primary_key_column)


@app.route('/register_staff', methods=['GET', 'POST'])
def register_staff():
    if request.method == 'POST':
        full_name = request.form['full_name_s']
        post = request.form['post_s']
        salary = int(request.form['salary_s'])
        email = request.form['email_s']
        phone_number = request.form['phone_number_s']
        experience = int(request.form['experience_s'])
        brief_information = request.form['brief_information_s']
        login = request.form['login_s']
        password = request.form['password_s']
        confirm_password = request.form['confirm_password']
        name_role = request.form['name_role_s']

        if password != confirm_password:
            return "Passwords do not match"

        hashed_password = hash_password(password)

        staff_id = session['staff_id']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name_cod FROM staff WHERE id_staff = %s", (staff_id,))
        admin_name_cod = cur.fetchone()
        name_cod = admin_name_cod[0]

        cur.execute("INSERT INTO staff (full_name, post, salary, email, phone_number, experience, brief_information, name_cod, login, password_hash, name_role, password) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (full_name, post, salary, email, phone_number, experience, brief_information, name_cod, login, hashed_password, name_role, password))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('admin_page', staff_id=session['staff_id']))

    return render_template('register_staff.html')


if __name__ == '__main__':
    app.run(debug=True)

