"""
centralized_log_api.py

This module provides a Flask application for a centralized logging system.
"""

from flask import Flask, request, jsonify, g
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Union

app = Flask(__name__)
DATABASE: str = 'centralized_log.db'


def connect_db() -> sqlite3.Connection:
    """
    Establishes a connection to the SQLite database.

    Returns:
        sqlite3.Connection: The SQLite database connection.
    """
    
    return sqlite3.connect(DATABASE)


def init_db() -> None:
    """
    Initializes the database by creating tables defined in 'schema.sql'.
    """

    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db() -> sqlite3.Connection:
    """
    Retrieves the current database connection from the global context.

    Returns:
        sqlite3.Connection: The SQLite database connection.
    """

    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error: Optional[Exception]):
    """
    Closes the database connection when the Flask app context is torn down.

    Args:
        error (Optional[Exception]): Any exception that occurred.
    """

    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/logs', methods=['GET'])
def get_all_logs() -> str:
    """
    Retrieves all logs from the database.

    Returns:
        str: JSON-formatted string containing the logs.
    """

    db = get_db()
    cursor = db.execute('SELECT * FROM logs')
    logs = cursor.fetchall()
    return jsonify(logs)


@app.route('/logs/system/<system>', methods=['GET'])
def get_logs_by_system(system: str) -> str:
    """
    Retrieves logs for a specific system from the database.

    Args:
        system (str): The name of the system.

    Returns:
        str: JSON-formatted string containing the logs for the specified system.
    """

    db = get_db()
    cursor = db.execute('SELECT * FROM system WHERE name = ?', (system,))
    logs = cursor.fetchall()
    return jsonify(logs)


@app.route('/logs/date/<date>', methods=['GET'])
def get_logs_by_date(date: str) -> str:
    """
    Retrieves logs on or before a specified date from the database.

    Args:
        date (str): The date in 'YYYY-MM-DD' format.

    Returns:
        str: JSON-formatted string containing the logs on or before the specified date.
    """

    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    db = get_db()
    cursor = db.execute('SELECT * FROM logs WHERE log_date <= ?', (date_obj,))
    logs = cursor.fetchall()
    return jsonify(logs)


@app.route('/systems', methods=['POST'])
def add_system() -> str:
    """
    Adds a new system to the database.

    Returns:
        str: JSON-formatted string indicating the success or failure of the operation.
    """

    data = request.get_json()
    name = data.get('name')
    ip_address = data.get('ip_address')

    if not name:
        return jsonify({'error': 'System name is required'}), 400

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO system (name, ip_address) VALUES (?, ?)', (name, ip_address))
    conn.commit()
    conn.close()

    return jsonify({'message': 'System added successfully'}), 201


@app.route('/logs', methods=['POST'])
def add_log_entry() -> str:
    """
    Adds a new log entry to the database.

    Returns:
        str: JSON-formatted string indicating the success or failure of the operation.
    """

    data = request.get_json()
    system_name = data.get('system_name')
    log_date = data.get('log_date')
    log_level = data.get('log_level')
    message = data.get('message')
    directory = data.get('directory')

    if not system_name or not log_date or not log_level or not message:
        return jsonify({'error': 'System name, log date, log level, and message are required'}), 400

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('SELECT system_id FROM system WHERE name = ?', (system_name,))
    system_id = cursor.fetchone()

    if not system_id:
        return jsonify({'error': 'System not found'}), 404

    cursor.execute(
        'INSERT INTO logs (system_id, log_date, log_level, message, directory) VALUES (?, ?, ?, ?, ?)',
        (system_id[0], log_date, log_level, message, directory))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Log entry added successfully'}), 201


@app.route('/logs/delete-before/<date>', methods=['DELETE'])
def delete_logs_before_date(date: str) -> str:
    """
    Deletes logs before a specified date from the database.

    Args:
        date (str): The date in 'YYYY-MM-DD' format.

    Returns:
        str: JSON-formatted string indicating the success or failure of the operation.
    """

    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    db = get_db()
    db.execute('DELETE FROM logs WHERE log_date < ?', (date_obj,))
    db.commit()

    return jsonify({'status': 'Logs deleted successfully'})


@app.route('/logs/update/<int:log_id>', methods=['PUT'])
def update_log(log_id: int) -> str:
    """
    Updates an existing log entry in the database.

    Args:
        log_id (int): The ID of the log entry to be updated.

    Returns:
        str: JSON-formatted string indicating the success or failure of the operation.
    """

    data = request.json
    system = data.get('system')
    log_level = data.get('log_level')
    message = data.get('message')
    directory = data.get('directory')

    db = get_db()
    db.execute('UPDATE logs SET system_id=?, log_level=?, message=?, directory=? WHERE log_id=?',
               (system, log_level, message, directory, log_id))
    db.commit()

    return jsonify({'status': 'Log entry updated successfully'})


if __name__ == '__main__':
    app.run(debug=True)
