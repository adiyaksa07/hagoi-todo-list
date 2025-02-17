import secrets
import bcrypt 
import MySQLdb.cursors
import os
import dotenv

dotenv.load_dotenv()

from datetime import datetime
from flask import Flask, render_template, session, redirect, url_for, request, flash
from flask_mysqldb import MySQL

application = Flask(__name__)

application.config['SECRET_KEY'] = secrets.token_hex(32) 
application.config['MYSQL_HOST'] = os.getenv("HOST")
application.config['MYSQL_USER'] = os.getenv("USER")
application.config['MYSQL_PASSWORD'] = os.getenv("PASSWORD")
application.config['MYSQL_DB'] = "prod_hagoi_todo_db"

mysql = MySQL(application)

@application.route("/")
def home():
    if 'logged' not in session:
        return redirect(url_for('login'))

    if 'task_submitted' in session:
        session.pop('task_submitted')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s", (session['user_id'],))
    tasks = cursor.fetchall()
    cursor.close()

    return render_template("index.jinja2", tasks=tasks)

@application.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        if 'logged' in session:
            return redirect(url_for('home'))
        
        return render_template("login.jinja2")
    elif request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['username'] = username
            session['user_id'] = user['id']
            session['logged'] = True
            return redirect(url_for('home'))
        else:
            flash('Username atau password salah!', 'error')
            return render_template("index.jinja2")

    
@application.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        if 'logged' in session: 
            return redirect(url_for('home'))

        return render_template("register.jinja2")
    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if username == "":
            flash("Username anda kosong!", "error")
            return render_template("register.jinja2")

        if password == "": 
            flash("Password anda kosong!", "error")
            return render_template("register.jinja2")
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Username sudah digunakan, silakan pilih username lain!", "error")
            return render_template("register.jinja2")

        if password == confirm_password: 
            bytes = password.encode('utf-8') 
            salt = bcrypt.gensalt() 
            hash = bcrypt.hashpw(bytes, salt) 

            cursor = mysql.connection.cursor()

            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hash))
            mysql.connection.commit()
            cursor.close()

            flash('Registrasi berhasil, Silakan login!', 'success')
            return redirect(url_for('login'))
        else:
            flash("Pastikan password dan konfirmasi password sama!", "error")
            return render_template("register.jinja2") 

@application.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@application.route("/add-data", methods=['POST'])
def add_task():
    if 'logged' not in session:
        return redirect(url_for('login'))
    
    task_text = request.form.get("task")
    priority = request.form.get("priority") 
    due_date = request.form.get("due_date")
    
    try:
        due_date_str = request.form.get("due_date")
        due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")
    except:
        flash("Tolong masukan data dengan benar!", "error")
        return redirect(url_for("home")) 

    if task_text:
        if 'task_submitted' in session:
            return redirect(url_for("home"))
         
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO tasks (user_id, text, priority, due_date) VALUES (%s, %s, %s, %s)", 
                       (session['user_id'], task_text, priority, due_date))
        mysql.connection.commit()
        cursor.close()
    
    return redirect(url_for('home'))

@application.route("/mark-done/<int:task_id>")
def mark_done(task_id):
    if 'logged' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE tasks SET is_done = TRUE WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    mysql.connection.commit()
    cursor.close()
    
    return redirect(url_for('home'))

@application.route("/delete-task/<int:task_id>")
def delete_task(task_id):
    if 'logged' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    mysql.connection.commit()
    cursor.close()
    
    return redirect(url_for('home'))

@application.route("/edit-task/<int:task_id>", methods=['GET', 'POST'])
def edit_task(task_id):
    if 'logged' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM tasks WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    task = cursor.fetchone()
    cursor.close()

    if request.method == "POST":
        new_text = request.form.get("task")
        new_priority = request.form.get("priority")
        
        try:
            due_date_str = request.form.get("due_date")
            new_due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")
        except:
            flash("Tolong masukan data dengan benar!", "error")
            return redirect(url_for("home"))
    
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE tasks SET text = %s, priority = %s, due_date = %s WHERE id = %s AND user_id = %s",
                       (new_text, new_priority, new_due_date, task_id, session['user_id']))
        mysql.connection.commit()
        cursor.close()
        
        return redirect(url_for('home'))
    
    return render_template("edit_task.jinja2", task=task)

@application.route("/profile", methods=['GET', 'POST'])
def profile():
    if 'logged' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_username = request.form.get("username")
        new_password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute("SELECT * FROM users WHERE username = %s AND id != %s", (new_username, session['user_id']))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Username sudah digunakan, silakan pilih yang lain!", "error")
            return redirect(url_for('profile'))

        cursor.execute("UPDATE users SET username = %s WHERE id = %s", (new_username, session['user_id']))
        session['username'] = new_username

        if new_password:
            if new_password != confirm_password:
                flash("Password tidak cocok, coba lagi!", "error")
                return redirect(url_for('profile'))

            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, session['user_id']))

        mysql.connection.commit()
        cursor.close()

        flash("Profil berhasil diperbarui!", "success")
        return redirect(url_for('profile'))

    return render_template("profile.jinja2")

if __name__ == "__main__": 
    application.run(debug=False)
