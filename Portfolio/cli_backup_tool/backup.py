"""
Backup.py: A script for performing file backups and logging as well

Includes functions such as setting up logging, creating and querying a SQLite database, displaying information from it and making backups itself

"""

import os
import shutil
import argparse
import logging
from datetime import datetime
import sqlite3
import hashlib
import time
import sys
from typing import Optional, Tuple, Union

def setup_logger(log_filename: str, verbose: bool, db_name: str) -> logging.Logger:
    """Logger

    Set up a logger for the backup tool

    Args:
        log_filename (str): The name of the log file.
        verbose (bool): Flag to enable verbose logging.
        db_name (str): Name of the SQLite database.

    Returns:
        logging.Logger: Configured logger object
    """

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


def get_md5_hash(file_path: str) -> Optional[str]:
    """
    Calculate MD5 hash for a given file.

    Args:
        file_path (str): Path to the file.

    Returns:
        str or None: MD5 hash of the file, or None if the file does not exist.
    """

    if os.path.isfile(file_path):
        file_content = open(file_path, "rb").read()
        hash_value = hashlib.md5(file_content).hexdigest()
        return hash_value
    else:
        return None


def create_database(db_name: str) -> None:
    """
    Create a SQLite database with necessary tables for file backup.

    Args:
        db_name (str): Name of the SQLite database.
    """
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

def insert_file_info(
    db_name: str,
    directory: str,
    filename: str,
    last_backup_datetime: str,
    md5hash: str
) -> None:
    """
    Insert file information into the 'file' table in the SQLite database.

    Args:
        db_name (str): Name of the SQLite database.
        directory (str): Directory of the file.
        filename (str): Name of the file.
        last_backup_datetime (str): Last backup datetime in string format.
        md5hash (str): MD5 hash of the file content.

    Returns:
        None
    """

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO file (Directory, Filename, Last_backup_datetime, Md5hash)
        VALUES (?, ?, ?, ?)
    ''', (directory, filename, last_backup_datetime, md5hash))
    conn.commit()
    conn.close()


def create_notes_table(db_name: str) -> None:
    """
    Create the 'Notes' table in the SQLite database if it does not exist.

    Args:
        db_name (str): Name of the SQLite database.

    Returns:
        None
    """

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


def create_logentry_table(db_name: str) -> None:
    """
    Create the 'Logentry' table in the SQLite database if it does not exist.

    Args:
        db_name (str): Name of the SQLite database.

    Returns:
        None
    """

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


def insert_log_entry(
    db_name: str,
    entry_datetime: str,
    severity_level: str,
    message: str,
    file_id: int = None,
    job_id: int = None
) -> int:
    """
    Insert a log entry into the 'Logentry' table in the SQLite database.

    Args:
        db_name (str): Name of the SQLite database.
        entry_datetime (str): Datetime of the log entry.
        severity_level (str): Severity level of the log entry.
        message (str): Log message.
        file_id (int, optional): ID of the associated file.
        job_id (int, optional): ID of the associated backup job.

    Returns:
        int: ID of the inserted log entry.
    """

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


def create_backup_job_table(db_name: str) -> None:
    """
    Create the 'BackupJob' table in the SQLite database if it does not exist.

    Args:
        db_name (str): Name of the SQLite database.

    Returns:
        None
    """

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


def insert_backup_job(
    db_name: str,
    commandline: str,
    execution_datetime: str
) -> int:
    """
    Insert a backup job entry into the 'BackupJob' table in the SQLite database.

    Args:
        db_name (str): Name of the SQLite database.
        commandline (str): Command line used for the backup job.
        execution_datetime (str): Datetime of the backup job execution.

    Returns:
        int: ID of the inserted backup job entry.
    """

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
def backup_files(
    source_dir: str,
    destination_dir: str,
    db_name: str,
    logger: logging.Logger,
    file_id: Optional[int] = None,
    job_id: Optional[int] = None
) -> None:
    """
    Backup files from the source directory to the destination directory.

    Args:
        source_dir (str): Source directory path.
        destination_dir (str): Destination directory path.
        db_name (str): Name of the SQLite database.
        logger (logging.Logger): Logger object for logging.
        file_id (int, optional): File ID for database reference.
        job_id (int, optional): Backup job ID for database reference.
    """

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
def query_files(db_name: str, directory: str, logger: logging.Logger) -> None:
    """
    Query files in a specific directory from the 'file' table in the SQLite database.

    Args:
        db_name (str): Name of the SQLite database.
        directory (str): Directory to query files for.
        logger (logging.Logger): Logger object for logging.

    Returns:
        None
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT Filename FROM file WHERE Directory = ?', (directory,))
    files = cursor.fetchall()
    conn.close()

    if files:
        logger.info(f"Files in directory '{directory}': {', '.join(file[0] for file in files)}")
    else:
        logger.info(f"No files found in directory '{directory}'")

def query_logs(db_name: str, directory: str, filename: str, date: str, logger: logging.Logger) -> None:
    """
    Query logs for a specific file in a directory from the 'Logentry' table in the SQLite database.

    Args:
        db_name (str): Name of the SQLite database.
        directory (str): Directory of the file.
        filename (str): Name of the file.
        date (str): Date for log filtering (optional).
        logger (logging.Logger): Logger object for logging.

    Returns:
        None
    """
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


def query_all_logs(db_name, directory, date, logger):
    """
    Query all logs for files in a specific directory.

    Args:
        db_name (str): Name of the SQLite database.
        directory (str): Directory to query logs for.
        date (str): Date for log filtering (optional).
        logger (logging.Logger): Logger object for logging.
    """

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
def display_backup_job_info(db_name: str, job_id: int, logger: logging.Logger) -> None:
    """
    Display information for a specific backup job from the 'BackupJob' table in the SQLite database.

    Args:
        db_name (str): Name of the SQLite database.
        job_id (int): ID of the backup job to display information for.
        logger (logging.Logger): Logger object for logging.

    Returns:
        None
    """
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

def display_job_logs(db_name: str, job_id: int, logger: logging.Logger) -> None:
    """
    Display log entries for a specific backup job from the 'Logentry' table in the SQLite database.

    Args:
        db_name (str): Name of the SQLite database.
        job_id (int): ID of the backup job to display logs for.
        logger (logging.Logger): Logger object for logging.

    Returns:
        None
    """
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
    """
    Main function for executing the backup tool from the command line.
    Parses command line arguments and triggers backup or query operations.
    """

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