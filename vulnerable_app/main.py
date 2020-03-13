import datetime
import logging
import os

from flask import Flask, render_template, request, Response
import sqlalchemy

db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_name = os.environ.get("DB_NAME")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

app = Flask(__name__)

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
            users.append({"username": row[0], "password": row[1]})
    return users

@app.before_first_request
def create_tables():
    # Create tables (if they don't already exist)
    with db.connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users "
            "( username VARCHAR(25) NOT NULL,"
            "password VARCHAR(50) NOT NULL, PRIMARY KEY (username) );"
        )

# @app.route("/", methods=["GET", "POST"])
# def index():
#     message = ""
#     if request.method == "POST":
#         user = request.form.get('username')
#         passw = request.form.get('password')
#
#         if user = 'root' and passw = '1234':
#             message = "user found"
#         else:
#             message = "user not found"
#
#     return render_template("index.html", message = message)

@app.route('/login/', methods=['post', 'get'])
def login():
    users = getUsers()
    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        find = {"username": username, "password": password}
        if find in users:
            message = "Correct username and password"
        else:
            message = "Wrong username or password"

    return render_template('index.html', message=message)

# @app.route('/create_account/', methods=['post', 'get'])
# def create_account():
#     if request.method = 'POST':
#         new_username = request.form.get('new_username')
#         new_password = request.form.get('new_username')
#
#         with db.connect() as conn:
#             conn.execute(
#                 f"INSERT INTO users VALUES ({new_username}, {new_password});"
#             )
#
#         return render_template("users.html", all_users=users, tab_count=0, space_count=0)
#     return render_template('create.html')

@app.route("/users/", methods=["GET"])
def users():
    users = getUsers()

    return render_template(
        "users.html", all_users=users, tab_count=0, space_count=0
    )

if __name__ == "__main__":
    app.run(debug=True)
