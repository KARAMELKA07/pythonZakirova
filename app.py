from flask import Flask, render_template, url_for, request, redirect
import psycopg2
import builtins

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

        # selected_services = request.form['services']
        selected_services = request.form.getlist('services[]')
        print(selected_services)
        selected_equipment = request.form.getlist('equipment[]')
        
        filtered_services = [rows[int(index)] for index in selected_services]
        filtered_equipment = [rows_second_table[int(index)] for index in selected_equipment]
        return render_template('order.html', services=filtered_services, equipment=filtered_equipment)


if __name__ == "__main__":
    app.run(debug=True)

@app.route('/home')
def index():
    return render_template("index.html")


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/user/<string:name>/<int:id>')
def user(name, id):
    return "User page: " + name + " - " + str(id)


