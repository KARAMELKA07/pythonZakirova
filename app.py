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
        print(selected_services)
        selected_equipment = request.form.getlist('equipment[]')
        
        filtered_services = [rows[int(index)] for index in selected_services]
        filtered_equipment = [rows_second_table[int(index)] for index in selected_equipment]
        print(filtered_services, filtered_equipment)
        return render_template('order.html', services=filtered_services, equipment=filtered_equipment, bonus=bonus)

@app.route('/submit_order', methods=['POST'])
def submit_order():
    print("кнопка нажалась")
    if 'user_id' not in session:
        return redirect(url_for('login_register'))

    user_id = session['user_id']
    selected_services = request.form.getlist('services[]')
    selected_equipment = request.form.getlist('equipment[]')
    print(selected_services)
    print(selected_equipment)

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
        service_index = int(index)
        service_id = rows[service_index][0]
        service_name = rows[service_index][1]
        service_cost = rows[service_index][2]*(100 - bonus) / 100
        services_data.append((service_id, service_name, service_cost))
    print(services_data)
    
    # Выбранное оборудование
    cur.execute("SELECT id_device, name_device, cost FROM equipment")
    rows_second_table = cur.fetchall()
    equipment_data = []
    for index in selected_equipment:
        equipment_index = int(index)
        equipment_id = rows_second_table[equipment_index][0]
        equipment_name = rows_second_table[equipment_index][1]
        equipment_cost = rows_second_table[equipment_index][2]*(100 - bonus) / 100
        equipment_data.append((equipment_id, equipment_name, equipment_cost))
    print(equipment_data)

    # Вставка данных в таблицу requests
    for user_id, service_cost, service_id in services_data:
        #cur.execute("INSERT INTO requests (id_client, finalcost, id_service) VALUES (%s, %s, %s)", (user_id, final_cost, service_id))
        print(user_id, service_cost, service_id)

    for user_id, equipment_cost, equipment_id in equipment_data:
        #cur.execute("INSERT INTO requests (id_client, finalcost, id_device) VALUES (%s, %s, %s)", (user_id, final_cost, equipment_id))
        print(user_id, equipment_cost, equipment_id)

    # Подтверждение изменений в базе данных
    conn.commit()

    # Закрытие курсора и соединения
    cur.close()
    conn.close()

    return 'Order submitted successfully!'



def hash_password(password, stored_password_hash=None):
    if stored_password_hash:
        salt = stored_password_hash[:29].encode('utf-8')  
    else:
        salt = bcrypt.gensalt()

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

    return hashed_password.decode('utf-8')


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

    if request.method == 'GET':
        return render_template("analyst.html", analyst_name=analyst_name)

    if request.method == 'POST':
        # Получение типа отчета
        report_type = request.form['report_type']

        # Вызов соответствующей функции для формирования отчета
        if report_type == 'total_income':
            cur.callproc('generate_total_income_report')
        elif report_type == 'centre_income':
            cur.execute("SELECT id_centre, centre_income FROM get_centre_income()")
            data = cur.fetchall()

            with open('centre_income_report.csv', 'w') as f:
                # Записываем заголовок
                f.write('id_centre, centre_income\n')
                
                for row in data:
                    f.write(f"{row[0]}, {row[1]}\n")



        elif report_type == 'top_income_employees':
            cur.callproc('generate_top_income_employees_report')
        
        # Подтверждение изменений в БД
        conn.commit()

        # Закрытие курсора и соединения
        cur.close()
        conn.close()

        return "Отчет сформирован успешно!"


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
        print(full_name, phone_number, username, password, hashed_password)
        conn.commit()
        cur.close()
        conn.close()
        
        return "Вы зарегистрированы"
    
    return render_template('register.html')




if __name__ == '__main__':
    app.run(debug=True)
