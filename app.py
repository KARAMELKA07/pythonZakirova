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
                    return redirect(url_for('user_page', user_id = user_id))
                else:
                    print('Неверный логин, пароль или роль')
                    # return render_template('login_register.html', roles=roles)
            else:
                print('Неверный логин, пароль или роль')
                # return render_template('login_register.html', roles=roles)
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
                        return redirect(url_for('analyst_page', staff_id = staff_id))
                else:
                    print('Неверный логин, пароль или роль')
                    # return render_template('login_register.html', roles=roles)
            else:
                print('Неверный логин, пароль или роль')
                # return render_template('login_register.html', roles=roles)
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
        print('263', full_name, phone_number, username, password, hashed_password)
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
        return redirect(url_for('submit_order', services=selected_services, equipment=selected_equipment, bonus=bonus))
    return render_template('order.html', services=services, equipment=equipment, bonus=0)


@app.route('/submit_order', methods=['GET', 'POST'])
def submit_order():
    
    if 'user_id' not in session:
        return redirect(url_for('login_register'))

    user_id = session['user_id']
    selected_services = request.args.getlist('services')
    selected_equipment = request.args.getlist('equipment')

    # Получение соединения с базой данных
    conn = get_db_connection()
    cur = conn.cursor()

    # Получение информации о пользователе
    cur.execute("SELECT bonus FROM clients WHERE id_client = %s", (user_id,))
    bonus = cur.fetchone()[0]

    # Выбранные услуги
    cur.execute("SELECT id_service, name_service, cost FROM service")
    rows = cur.fetchall()
    services_data = []
    for index in selected_services:
        service_index = int(index)-1
        service_id = rows[service_index][0]
        service_name = rows[service_index][1]
        service_cost = int(rows[service_index][2]*(100 - bonus) / 100)
        services_data.append((service_id, service_name, service_cost))
  
    
    # Выбранное оборудование
    cur.execute("SELECT id_device, name_device, cost FROM equipment")
    rows_second_table = cur.fetchall()
    equipment_data = []
    for index in selected_equipment:
        equipment_index = int(index)-1
        equipment_id = rows_second_table[equipment_index][0]
        equipment_name = rows_second_table[equipment_index][1]
        equipment_cost = int(rows_second_table[equipment_index][2]*(100 - bonus) / 100)
        equipment_data.append((equipment_id, equipment_name, equipment_cost))


    # Вставка данных в таблицу requests
    for service_id, service_name, service_cost in services_data:
        cur.execute("INSERT INTO requests (id_client, finalcost, id_service) VALUES (%s, %s, %s)", (user_id, service_cost, service_id))

    for equipment_id, equipment_name, equipment_cost in equipment_data:
        cur.execute("INSERT INTO requests (id_client, finalcost, id_device) VALUES (%s, %s, %s)", (user_id, equipment_cost, equipment_id))
        
    # Подтверждение изменений в базе данных
    conn.commit()

    # Закрытие курсора и соединения
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

    # Получение информации о сотруднике из БД
    cur.execute("SELECT full_name FROM staff WHERE id_staff = %s", (staff_id,))
    analyst_data = cur.fetchone()
    analyst_name = analyst_data[0]

    cur.execute("SELECT id_client, full_name, status, money_spent, bonus, phone_number, id_staff FROM clients")
    clients_data = cur.fetchall()

    if request.method == 'POST':
        # Получение типа отчета
        report_type = request.form['report_type']

        # Вызов соответствующей функции для формирования отчета
        if report_type == 'total_income':
            cur.execute('SELECT total_income FROM get_total_income()')
            data = cur.fetchone()[0]
            with open('total_income_report.csv', 'w') as f:
                # Записываем заголовок
                f.write('Общий доход по ЦОДам:\n')
                f.write(f"{data}\n")

        elif report_type == 'centre_income':
            cur.execute("SELECT name_cod, centre_income FROM get_centre_income()")
            data = cur.fetchall()

            with open('centre_income_report.csv', 'w') as f:
                # Записываем заголовок
                f.write('Центр, Доход центра\n')
                
                for row in data:
                    f.write(f"{row[0]}, {row[1]}\n")


        elif report_type == 'top_income_employees':
            
            cur.execute('SELECT * FROM get_top_income_employees()')
            data = cur.fetchall()
            with open('top_income_employees_report.csv', 'w') as f:
                # Записываем заголовок
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
                # Записываем заголовок
                f.write('Статус, Количество клиентов\n')
                
                for row in data:
                    f.write(f"{row[0]}, {row[1]}\n")

        # Подтверждение изменений в БД
        conn.commit()

        return "Отчет сформирован успешно!"
    
    # Закрытие курсора и соединения
    cur.close()
    conn.close()

    return render_template("analyst.html", analyst_name=analyst_name, clients=clients_data)



def get_table_data(table_name):
    
    conn = get_db_connection()

    cur = conn.cursor()
    if table_name=='clients':
        cur.execute(f"SELECT id_client, full_name, status, money_spent, bonus, phone_number, id_staff FROM {table_name}")
    elif table_name=='staff':
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



if __name__ == '__main__':
    app.run(debug=True)
