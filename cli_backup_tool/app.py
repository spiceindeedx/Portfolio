from flask import Flask, render_template, redirect, request, url_for
import sqlite3

app = Flask(__name__)

def connect_db():
    return sqlite3.connect("backup_database.db")

def get_recent_logs():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT Logentry.entry_datetime, Logentry.severity_level, Logentry.Message, file.Directory, file.Filename
    FROM Logentry
    LEFT JOIN file ON Logentry.file_id = file.File_id
    WHERE Logentry.severity_level IN ('ERROR', 'WARNING')
    ORDER BY Logentry.entry_datetime ASC
    LIMIT 10
    ''')
    logs = cursor.fetchall()
    conn.close()
    return logs

def get_all_files():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT File_id, Directory, Filename
        FROM file
    ''')
    files = cursor.fetchall()
    conn.close()
    return files

def get_file_info(file_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT File_id, Directory, Filename, Last_backup_datetime, Md5hash
        FROM file
        WHERE File_id = ?
    ''', (file_id,))
    file_info = cursor.fetchone()

    cursor.execute('''
        SELECT entry_datetime, severity_level, Message, entry_id
        FROM Logentry
        WHERE file_id = ?
    ''', (file_id,))
    log_entries = cursor.fetchall()
    
    log_notes = {}  # Add this line to define log_notes

    for log in log_entries:
        cursor.execute("SELECT * FROM Notes WHERE entry_id=?", (log[3],))
        attached_notes = cursor.fetchall()

        # Extract the second element (note) from each row and store it in the dictionary
        log_notes[log[3]] = [row[1] for row in attached_notes]
    """print(file_info)"""
    conn.close()
    return file_info, log_entries, log_notes

@app.route('/')
def home():
    recent_logs = get_recent_logs()
    return render_template('index.html', logs=recent_logs)

@app.route('/filepage')
def filepage():
    all_files = get_all_files()
    return render_template('filepage.html', files=all_files)

@app.route('/attach_note/<file_id>/<entry_id>', methods=['POST'])
def attach_note(file_id,entry_id):
    note_text = request.form.get('note_text')
    try:
        if note_text:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Notes (note_text, entry_id) VALUES (?, ?)", (note_text, entry_id))
            conn.commit()
            conn.close()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    return redirect(url_for('file_info', file_id=file_id))

@app.route('/file/<int:file_id>')
def file_info(file_id):
    file_info, log_entries, log_notes = get_file_info(file_id)
    return render_template('file_info.html', file_info=file_info, log_entries=log_entries, log_notes=log_notes)

if __name__ == '__main__':
    app.run(debug=True)
