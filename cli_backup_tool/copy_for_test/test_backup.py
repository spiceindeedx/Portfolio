# test_backup.py
import sqlite3
import os
import shutil
from datetime import datetime, timedelta
import pytest
from backup import (
    setup_logger,
    get_md5_hash,
    create_database,
    insert_file_info,
    create_notes_table,
    create_logentry_table,
    insert_log_entry,
    create_backup_job_table,
    insert_backup_job,
    backup_files,
    query_files,
    query_logs,
    query_all_logs,
    display_backup_job_info,
    display_job_logs,
)

# Test data
TEST_SOURCE_DIR = "test_source"
TEST_DESTINATION_DIR = "test_destination"
TEST_DB_NAME = "test_database.db"
TEST_LOG_FILENAME = "test_backup.log"

@pytest.fixture
def logger():
    return setup_logger(TEST_LOG_FILENAME, verbose=False, db_name=TEST_DB_NAME)

def test_setup_logger(logger):
    assert logger is not None

def test_get_md5_hash(tmp_path):
    file_content = b'Test file content'
    test_file = tmp_path / "test_file.txt"
    test_file.write_bytes(file_content)

    md5_hash = get_md5_hash(test_file)
    assert md5_hash is not None
    assert len(md5_hash) == 32

def test_create_database(tmp_path):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)
    assert os.path.exists(test_db_name)

def test_insert_file_info(tmp_path):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)

    insert_file_info(test_db_name, "test_directory", "test_file.txt", "2022-01-01 12:00:00", "test_md5_hash")

    conn = sqlite3.connect(test_db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM file')
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[1] == "test_directory"
    assert result[2] == "test_file.txt"

def test_create_notes_table(tmp_path):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)
    create_notes_table(test_db_name)

    conn = sqlite3.connect(test_db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="Notes"')
    result = cursor.fetchone()
    conn.close()

    assert result is not None

def test_create_logentry_table(tmp_path):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)
    create_logentry_table(test_db_name)

    conn = sqlite3.connect(test_db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="Logentry"')
    result = cursor.fetchone()
    conn.close()

    assert result is not None

def test_insert_log_entry(tmp_path):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)
    create_logentry_table(test_db_name)

    entry_id = insert_log_entry(test_db_name, "2022-01-01 12:00:00", "INFO", "Test log message", file_id=1, job_id=1)

    conn = sqlite3.connect(test_db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Logentry WHERE entry_id = ?', (entry_id,))
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[2] == "INFO"  
    assert result[3] == "2022-01-01 12:00:00"


def test_create_backup_job_table(tmp_path):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)
    create_backup_job_table(test_db_name)

    conn = sqlite3.connect(test_db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="BackupJob"')
    result = cursor.fetchone()
    conn.close()

    assert result is not None

def test_insert_backup_job(tmp_path):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)
    create_backup_job_table(test_db_name)

    job_id = insert_backup_job(test_db_name, "test_commandline", "2022-01-01 12:00:00")

    conn = sqlite3.connect(test_db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM BackupJob WHERE Job_id = ?', (job_id,))
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[1] == "test_commandline"
    assert result[2] == "2022-01-01 12:00:00"

def test_backup_files(tmp_path, logger):
    test_source_dir = tmp_path / "test_source"
    test_destination_dir = tmp_path / "test_destination"
    test_db_name = tmp_path / "test_db.db"

    os.makedirs(test_source_dir, exist_ok=True)
    os.makedirs(test_destination_dir, exist_ok=True)

    test_file_content = b'Test file content'
    test_file = test_source_dir / "test_file.txt"
    test_file.write_bytes(test_file_content)

    create_database(test_db_name)
    create_logentry_table(test_db_name)
    create_backup_job_table(test_db_name)

    file_id = 1
    job_id = 1

    backup_files(test_source_dir, test_destination_dir, test_db_name, logger, file_id=file_id, job_id=job_id)

    conn = sqlite3.connect(test_db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Logentry WHERE file_id = ?', (file_id,))
    result = cursor.fetchone()
    conn.close()

    assert result is not None
    assert result[4] == job_id

def test_query_files(tmp_path, logger, capsys):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)

    insert_file_info(test_db_name, "test_directory", "test_file.txt", "2022-01-01 12:00:00", "test_md5_hash")

    query_files(test_db_name, "test_directory", logger)

    captured = capsys.readouterr()
    assert "Files in directory 'test_directory': test_file.txt" in captured.out


def test_query_logs(tmp_path, logger, capsys):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)
    create_logentry_table(test_db_name)

    entry_datetime = datetime.now() - timedelta(days=1)
    entry_datetime_str = entry_datetime.strftime("%Y-%m-%d %H:%M:%S")

    insert_log_entry(test_db_name, entry_datetime_str, "INFO", "Test log message", file_id=1, job_id=1)

    query_logs(test_db_name, "test_directory", "test_file.txt", entry_datetime_str, logger)

    captured = capsys.readouterr()
    assert "Logs for file 'test_file.txt' in directory 'test_directory':" in captured.out

def test_query_all_logs(tmp_path, logger, capsys):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)
    create_logentry_table(test_db_name)

    entry_datetime = datetime.now() - timedelta(days=1)
    entry_datetime_str = entry_datetime.strftime("%Y-%m-%d %H:%M:%S")

    insert_log_entry(test_db_name, entry_datetime_str, "INFO", "Test log message", file_id=1, job_id=1)

    query_all_logs(test_db_name, "test_directory", entry_datetime_str, logger)

    captured = capsys.readouterr()
    assert "All logs for files in directory 'test_directory':" in captured.out

def test_display_backup_job_info(tmp_path, logger, capsys):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)
    create_backup_job_table(test_db_name)

    job_id = insert_backup_job(test_db_name, "test_commandline", "2022-01-01 12:00:00")

    display_backup_job_info(test_db_name, job_id, logger)

    captured = capsys.readouterr()
    assert "Backup Job Information:" in captured.out

def test_display_job_logs(tmp_path, logger, capsys):
    test_db_name = tmp_path / "test_db.db"
    create_database(test_db_name)
    create_logentry_table(test_db_name)

    entry_datetime = datetime.now() - timedelta(days=1)
    entry_datetime_str = entry_datetime.strftime("%Y-%m-%d %H:%M:%S")

    insert_log_entry(test_db_name, entry_datetime_str, "INFO", "Test log message", file_id=1, job_id=1)

    display_job_logs(test_db_name, 1, logger)

    captured = capsys.readouterr()
    assert "Logs for Backup Job ID 1:" in captured.out
