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

@app.before_first_request
def create_tables():
    # Create tables (if they don't already exist)
    with db.connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users "
            "( username VARCHAR(25) NOT NULL,"
            "password VARCHAR(50) NOT NULL, PRIMARY KEY (username) );"
        )

@app.route("/", methods=["GET"])
def index():
    users = []
    with db.connect() as conn:
        # Execute the query and fetch all results
        all_users = conn.execute(
            "SELECT username, password FROM users"
        ).fetchall()
        # Convert the results into a list of dicts representing votes
        for row in all_users:
            users.append({"username": row[0], "password": row[1]})

    return render_template(
        "index.html", all_users=users, tab_count=0, space_count=0
    )

if __name__ == "__main__":
    app.run(debug=True)
