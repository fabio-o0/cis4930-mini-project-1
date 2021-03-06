import datetime
import logging
import os

import random
import string
import re

import hashlib

from flask import Flask, render_template, request, Response, redirect, url_for, session, make_response
import sqlalchemy

db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_name = os.environ.get("DB_NAME")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

app = Flask(__name__)
app.secret_key = 'secret'

logger = logging.getLogger()

db = sqlalchemy.create_engine(
    sqlalchemy.engine.url.URL(
        drivername="mysql+pymysql",
        username=db_user,
        password=db_pass,
        database=db_name,
        query={"unix_socket": "/cloudsql/{}".format(cloud_sql_connection_name)},
    ),
    # Pool size is the maximum number of permanent connections to keep.
    pool_size=5,
    # Temporarily exceeds the set pool_size if no connections are available.
    max_overflow=2,
    pool_timeout=30,  # 30 seconds
    pool_recycle=1800,  # 30 minutes
)

def getUsers():
    users = []
    with db.connect() as conn:
        all_users = conn.execute(
            "SELECT username, password FROM users"
        ).fetchall()
        for row in all_users:
            users.append(row[0])
    return users

def strip_html(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def randomSalt():
    pool = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(pool) for i in range (16))

@app.before_first_request
def create_tables():
    with db.connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "username VARCHAR(25) PRIMARY KEY,"
            "password VARCHAR(256),"
            "salt VARCHAR(64)"
            ");"
        )

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route("/dashboard/<user>", methods=["GET", "POST"])
def dashboard(user):
    if request.cookies.get('logged_in') == 'true':
        if user != '':
            username = user
        else:
            username = request.cookies.get('last_user')
        result = ''
        script = ''
        user_found = ''
        if request.method == 'POST':
            to_find = request.form.get('search')
            users = getUsers()
            vulnerable = 'op'
            try:
                vulnerable = re.findall("^(.+?)'", to_find)[0]
            except:
                vulnerable = 'op'
            if to_find in users or vulnerable in users:
                if username == to_find or username == vulnerable:
                    with db.connect() as conn:
                        user_found = conn.execute(
                            f"SELECT * FROM users WHERE username='{to_find}'"
                        ).fetchall()
                else:
                    with db.connect() as conn:
                        user_found = conn.execute(
                            f"SELECT username FROM users WHERE username='{to_find}'"
                        ).fetchall()
            elif "<" in to_find:
                script = strip_html(to_find)
            else:
                user_found = 'not found'
            if user_found != 'not found':
                result = f'Query returned {user_found}'
            else:
                result = 'Query returned empty'
        return render_template("dashboard.html", user=username, result=result, script=script)
    #MORE SECURE METHOD
    # if 'logged_in' in session:
    #     if session['logged_in'] == 'true':
    #         username = session['user']
    #         return render_template("dashboard.html", user=username)
    return redirect(url_for('login'))

@app.route('/logout/')
def logout():
    if request.cookies.get('logged_in') == 'true':
        response = make_response(redirect(url_for('index')))
        response.set_cookie('logged_in', 'false')
        return response
    #MORE SECURE METHOD
    # if 'logged_in' in session:
    #     session.pop('logged_in', None)
    #     return redirect(url_for('index'))
    else:
        return "an error occurred"

@app.route('/login/', methods=['post', 'get'])
def login():
    if request.cookies.get('logged_in') == 'true':
        return redirect(url_for('dashboard', user = request.cookies.get('last_user')))
    #MORE SECURE METHOD
    # if 'logged_in' in session:
    #     if session['logged_in'] == 'true':
    #         return redirect(url_for('dashboard'))
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        salt = ''
        actual_pass = ''
        try:
            with db.connect() as conn:
                result = conn.execute(
                    f"SELECT salt, password FROM users WHERE username='{username}'"
                ).fetchall()
                for row in result:
                    salt = row[0]
                    actual_pass = row[1]
        except:
            return "an error occurred"

        try_pass = salt + password + os.environ.get("PEPPER")
        hashed = hashlib.md5(try_pass.encode())
        hashed_s = hashed.hexdigest()

        if hashed_s == actual_pass:
            message = "Successfully logged in"
            response = redirect(url_for('dashboard', user = username))
            response.set_cookie('last_user', username)
            response.set_cookie('logged_in', 'true')
            return response
            #MORE SECURE METHOD
            # session['user'] = username
            # session['logged_in'] = 'true'
            # return redirect(url_for('dashboard'))
        else:
            message = "Wrong username or password"

    return render_template('login.html', message=message)

@app.route('/create_account/', methods=['post', 'get'])
def create_account():
    message = ''
    if request.method == 'POST':
        username = request.form.get('new_username')
        password = request.form.get('new_password')

        salt = randomSalt()
        password = salt + password + os.environ.get("PEPPER")
        hash_pass = hashlib.md5(password.encode())
        hash_pass_s = hash_pass.hexdigest()

        with db.connect() as conn:
            try:
                conn.execute(
                    f"INSERT INTO users VALUES ('{username}', '{hash_pass_s}', '{salt}');"
                )
                return render_template('create.html', message= 'Account created. Please go back and log in.')
            except:
                return render_template('create.html', message='Username already taken. Please choose a different username')

    return render_template('create.html', message=message)

@app.route("/users/", methods=["GET"])
def users():
    users = []
    with db.connect() as conn:
        all_users = conn.execute(
            "SELECT username, password, salt FROM users"
        ).fetchall()
        for row in all_users:
            users.append({"username": row[0], "password": row[1], "salt": row[2]})

    return render_template(
        "users.html", all_users=users, tab_count=0, space_count=0
    )

if __name__ == "__main__":
    app.run(debug=True)
