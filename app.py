from flask import Flask, render_template, url_for, request, redirect, session
import psycopg2
import builtins
import bcrypt 

app = Flask(__name__)

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


@app.route('/', methods=['GET', 'POST'])
def index():
    
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id_device, name_device, cost FROM equipment")
    rows_second_table = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]

    cur.execute("SELECT id_service, name_service, cost FROM service")
    rows = cur.fetchall()
    column_names_second_table = [desc[0] for desc in cur.description]
    

    cur.close()
    conn.close()

    if request.method == 'GET':
        return render_template("request.html", data=rows, column_names=column_names, data_second_table=rows_second_table, column_names_second_table=column_names_second_table)
    
    if request.method == 'POST':

        selected_services = request.form.getlist('services[]')
        print(selected_services)
        selected_equipment = request.form.getlist('equipment[]')
        
        filtered_services = [rows[int(index)] for index in selected_services]
        filtered_equipment = [rows_second_table[int(index)] for index in selected_equipment]
        return render_template('order.html', services=filtered_services, equipment=filtered_equipment)



def hash_password(password, stored_password_hash=None):
    if stored_password_hash:
        salt = stored_password_hash[:29].encode('utf-8')  
    else:
        salt = bcrypt.gensalt()

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

    return hashed_password.decode('utf-8')

roles = ['пользователь', 'аналитик', 'менеджер', 'администратор']

@app.route('/login', methods=['GET', 'POST'])
def login_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        c = conn.cursor()
        
        if role == 'пользователь':
            c.execute("SELECT password_hash FROM clients WHERE login = %s", (username,))
            result = c.fetchone()

            if result:
                stored_password_hash, stored_role = result

                hashed_password = hash_password(password, stored_password_hash)
                if hashed_password == stored_password_hash:
                    print('Успешный вход')
                else:
                    print('Неверный логин, пароль или роль')
                    # return render_template('login_register.html', roles=roles)
            else:
                print('Неверный логин, пароль или роль')
                # return render_template('login_register.html', roles=roles)
        else:    
            c.execute("SELECT password_hash, name_role FROM staff WHERE login = %s", (username,))
            result = c.fetchone()

            if result:
                stored_password_hash, stored_role = result

                hashed_password = hash_password(password, stored_password_hash)
                if hashed_password == stored_password_hash and role == stored_role:
                    print('Успешный вход')
                else:
                    print('Неверный логин, пароль или роль')
                    # return render_template('login_register.html', roles=roles)
            else:
                print('Неверный логин, пароль или роль')
                # return render_template('login_register.html', roles=roles)

    return render_template('login_register.html', roles=roles)

