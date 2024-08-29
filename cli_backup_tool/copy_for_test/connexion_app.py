import os
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, g
import connexion

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///centralized_log.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Connexion application
connex_app = connexion.FlaskApp(__name__, specification_dir='.')
connex_app.add_api('centralized_server_spi.yml')


def connect_db():
    return sqlite3.connect('centralized_log.db')


def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/')
def home():
    return jsonify({'message': 'Centralized Log API'})


if __name__ == '__main__':
    os.environ['LOG_LEVEL'] = 'debug'  # Set log level to 'debug'
    connex_app.run()
