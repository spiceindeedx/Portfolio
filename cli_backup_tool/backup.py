import os
import shutil
import argparse
import logging
from datetime import datetime
import sqlite3
import hashlib
import time
import sys

"""Logger"""
def setup_logger(log_filename, verbose, db_name):
    logger = logging.getLogger('backup_tool')
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    

    return logger


def get_md5_hash(file_path):
    if os.path.isfile(file_path):
        file_content = open(file_path, "rb").read()
        hash_value = hashlib.md5(file_content).hexdigest()
        return hash_value
    else:
        return None

"""Database"""
def create_database(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file (
            File_id INTEGER PRIMARY KEY,
            Directory TEXT NOT NULL,
            Filename TEXT NOT NULL,
            Last_backup_datetime TEXT,
            Md5hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def insert_file_info(db_name, directory, filename, last_backup_datetime, md5hash):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO file (Directory, Filename, Last_backup_datetime, Md5hash)
        VALUES (?, ?, ?, ?)
    ''', (directory, filename, last_backup_datetime, md5hash))
    conn.commit()
    conn.close()


def create_notes_table(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Notes (
            note_id INTEGER PRIMARY KEY,
            note_text TEXT NOT NULL,
            entry_id INTEGER,
            FOREIGN KEY (entry_id) REFERENCES Logentry(entry_id)
        )
    ''')
    conn.commit()
    conn.close()


def create_logentry_table(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Logentry (
            entry_id INTEGER PRIMARY KEY,
            entry_datetime TEXT NOT NULL,
            severity_level TEXT NOT NULL,
            Message TEXT NOT NULL,
            file_id INTEGER,
            job_id INTEGER,
            FOREIGN KEY (file_id) REFERENCES file(File_id),
            FOREIGN KEY (job_id) REFERENCES BackupJob(Job_id)
        )
    ''')
    conn.commit()
    conn.close()


def insert_log_entry(db_name, entry_datetime, severity_level, message, file_id=None, job_id=None):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Logentry (entry_datetime, severity_level, Message, file_id, job_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (entry_datetime, severity_level, message, file_id, job_id))
    conn.commit()
    entry_id = cursor.lastrowid
    conn.close()
    return entry_id


def create_backup_job_table(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS BackupJob (
            Job_id INTEGER PRIMARY KEY,
            Commandline TEXT NOT NULL,
            Execution_datetime TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()

def insert_backup_job(db_name, commandline, execution_datetime):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO BackupJob (Commandline, Execution_datetime)
        VALUES (?, ?)
    ''', (commandline, execution_datetime))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id

"""Making backup"""
def backup_files(source_dir, destination_dir, db_name, logger, file_id=None, job_id=None):
    try:
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        files = os.listdir(source_dir)

        for file in files:
            source_file_path = os.path.join(source_dir, file)
            destination_file_path = os.path.join(destination_dir, file)
            source_md5 = get_md5_hash(source_file_path)
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute('SELECT File_id FROM file WHERE Directory = ? AND Filename = ?', (source_dir, file))
            result = cursor.fetchone()
            conn.close()
            file_id = result[0] if result else None

            if source_md5:
                conn = sqlite3.connect(db_name)
                cursor = conn.cursor()
                cursor.execute('SELECT Md5hash FROM file WHERE Directory = ? AND Filename = ?', (source_dir, file))
                result = cursor.fetchone()
                conn.close()
                if result and result[0] == source_md5:
                    logger.info(f"{datetime.now()} - INFO - {source_file_path} - NO CHANGE, SKIPPING")
                else:
                    try:
                        shutil.copy2(source_file_path, destination_file_path)
                        logger.info(f"{datetime.now()} - INFO - {source_file_path} -> {destination_file_path} - SUCCESSFULLY COPIED")
                        last_backup_datetime = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
                        insert_file_info(db_name, source_dir, file, last_backup_datetime, source_md5)
                        conn = sqlite3.connect(db_name)
                        cursor = conn.cursor()
                        cursor.execute('SELECT File_id FROM file WHERE Directory = ? AND Filename = ?', (source_dir, file))
                        file_id = cursor.fetchone()[0]
                        conn.close()
                        """file_id = cursor.lastrowid"""
                        insert_log_entry(db_name, datetime.now(), "INFO", f"{source_file_path} -> {destination_file_path} - SUCCESSFULLY COPIED", file_id=file_id, job_id=job_id)
                        
                    except Exception as e:
                        error_message = f"{datetime.now()} - ERROR - {source_file_path} -> {destination_file_path} - {str(e)}"
                        logger.error(error_message)
                        insert_log_entry(db_name, datetime.now(), "ERROR", error_message, file_id=file_id, job_id=job_id)
            else:
                warning_message = f"{datetime.now()} - WARNING - {source_file_path} - Skipped due to invalid source file"
                logger.warning(warning_message)
                insert_log_entry(db_name, datetime.now(), "WARNING", warning_message, file_id=file_id, job_id=job_id)

    except Exception as e:
        error_message = f"{datetime.now()} - ERROR - An error occurred: {str(e)}"
        logger.error(error_message)
        insert_log_entry(db_name, datetime.now(), "ERROR", error_message, file_id=file_id, job_id=job_id)

"""Query/Display information"""
def query_files(db_name, directory, logger):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT Filename FROM file WHERE Directory = ?', (directory,))
    files = cursor.fetchall()
    conn.close()

    if files:
        logger.info(f"Files in directory '{directory}': {', '.join(file[0] for file in files)}")
    else:
        logger.info(f"No files found in directory '{directory}'")

def query_logs(db_name, directory, filename, date, logger):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    query = 'SELECT Logentry.entry_datetime, Logentry.severity_level, Logentry.Message FROM Logentry JOIN file ON Logentry.file_id = file.File_id WHERE file.Filename = ? AND file.Directory = ?'
    parameters = [directory, filename]

    if date:
        query += ' AND Logentry.entry_datetime >= ?'
        parameters.append(date)

    cursor.execute(query, parameters)
    logs = cursor.fetchall()
    conn.close()

    if logs:
        logger.info(f"Logs for file '{filename}' in directory '{directory}':")
        for log in logs:
            logger.info(f"{log[0]} - {log[1]} - {log[2]}")
    else:
        logger.info(f"No logs found for file '{filename}' in directory '{directory}'")

def query_all_logs(db_name, directory, date, logger):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    query = 'SELECT Logentry.entry_datetime, Logentry.severity_level, Logentry.Message FROM Logentry JOIN file ON Logentry.file_id = file.File_id WHERE file.Directory = ?'
    parameters = [directory]

    if date:
        query += ' AND Logentry.entry_datetime >= ?'
        parameters.append(date)

    cursor.execute(query, parameters)
    logs = cursor.fetchall()
    conn.close()

    if logs:
        logger.info(f"All logs for files in directory '{directory}':")
        for log in logs:
            logger.info(f"{log[0]} - {log[1]} - {log[2]}")
    else:
        logger.info(f"No logs found for files in directory '{directory}'")
    
"""Display"""
def display_backup_job_info(db_name, job_id, logger):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM BackupJob WHERE Job_id = ?', (job_id,))
    job_info = cursor.fetchone()
    conn.close()

    if job_info:
        logger.info(f"Backup Job Information:")
        logger.info(f"Job ID: {job_info[0]}")
        logger.info(f"Commandline: {job_info[1]}")
        logger.info(f"Execution Datetime: {job_info[2]}")
    else:
        logger.info(f"No information found for Job ID: {job_id}")

def display_job_logs(db_name, job_id, logger):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT Logentry.entry_datetime, Logentry.severity_level, Logentry.Message
        FROM Logentry
        WHERE job_id = ?
    ''', (job_id,))
    logs = cursor.fetchall()
    conn.close()

    if logs:
        logger.info(f"Logs for Backup Job ID {job_id}:")
        for log in logs:
            logger.info(f"{log[0]} - {log[1]} - {log[2]}")
    else:
        logger.info(f"No logs found for Backup Job ID: {job_id}")

"""CLI + Execution"""
def main():
    parser = argparse.ArgumentParser(description="Backup tool with database")
    parser.add_argument("-s", "--source", required=True, help="Source directory")
    parser.add_argument("-d", "--destination", required=True, help="Destination directory")
    parser.add_argument("-l", "--log", help="Log filename")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode (log successful copies)")
    parser.add_argument("-db", "--database", help="Path to the database file")

    parser.add_argument("-q1", "--query-files", help="Query files in a certain directory")
    parser.add_argument("-q2", "--query-logs", nargs=2, metavar=('directory', 'filename'), help="Query logs related to a certain file")
    parser.add_argument("-q3", "--query-all-logs", help="Query all logs for files in a certain directory")
    parser.add_argument("-dt", "--date", help="Filter logs by date")
    parser.add_argument("--display-job-info", type=int, help="Display information for a specific backup job")
    parser.add_argument("--display-job-logs", type=int, help="Display log entries for a specific backup job")

    args = parser.parse_args()

    source_dir = args.source
    destination_dir = args.destination

    log_filename = args.log
    verbose = args.verbose

    db_name = args.database or os.path.join(os.getcwd(), "backup_database.db")
    
    if log_filename:
        logger = setup_logger(log_filename, verbose, db_name)
    else:
        logger = setup_logger("backup.log", verbose, db_name)

    create_database(db_name)
    create_notes_table(db_name)
    create_logentry_table(db_name)
    create_backup_job_table(db_name)
    logger.info(f"{datetime.now()} - INFO - Backup job started")

    file_id = None
    job_id = insert_backup_job(db_name, ' '.join(sys.argv), datetime.now())
    
    if args.display_job_info:
        display_backup_job_info(db_name, args.display_job_info, logger)
    elif args.display_job_logs:
        display_job_logs(db_name, args.display_job_logs, logger)
    else:
        backup_files(source_dir, destination_dir, db_name, logger, file_id=file_id, job_id=job_id)

    if args.query_files:
        query_files(db_name, args.query_files, logger)
    
    elif args.query_logs:
        directory, filename = args.query_logs
        query_logs(db_name, filename, directory, args.date, logger)
    
    elif args.query_all_logs:
        query_all_logs(db_name, args.query_all_logs, args.date, logger)
    
    else:
        backup_files(source_dir, destination_dir, db_name, logger, file_id=file_id)

    logger.info(f"{datetime.now()} - INFO - Backup job finished")
    insert_log_entry(db_name, datetime.now(), 'INFO', "Backup job finished", file_id=file_id)

if __name__ == "__main__":
    main()