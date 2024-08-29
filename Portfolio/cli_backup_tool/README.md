Welcome to backup job app readme! (instructions file)

My app has following functionalities and arguments:

 ("-s", "--source", “Source directory")
 ("-d", "--destination", "Destination directory")
 ("-l", "--log", "Log filename")
 ("-v", "--verbose", "Verbose mode (log successful copies)")
 ("-db", "--database", "Path to the database file")
 ("-q1", "--query-files", "Query files in a certain directory")
 ("-q2", "--query-logs", "Query logs related to a certain file")
 ("-q3", "--query-all-logs", "Query all logs for files in a certain directory")
 ("-dt", "--date", "Filter logs by date")
 ("--display-job-info", "Display information for a specific backup job")
 ("--display-job-logs", "Display log entries for a specific backup job")


In order to create a backup for your directory you need to launch terminal, go to path with your backup.py file. After that you can create a backup of directory by the example below.

python3 backup.py -s /Users/spiceindeedx/Desktop/test_db  -d /Users/spiceindeedx/Desktop/backups -l log_file.log -v


Also there are provided opportunity to make query of the database

Query the database to display a list of all files from a certain directory. (The directory is a parameter to your script):

python3 backup.py -s /Users/spiceindeedx/Desktop/test_db  -d /Users/spiceindeedx/Desktop/backups -l query_log.log -v -q1 /Users/spiceindeedx/Desktop/test_db

Query the database to display a list of all log messages related to a certain file. (The directory and filename are parameters to your script):

python3 app.py -s /Users/spiceindeedx/Desktop/test_db  -d /Users/spiceindeedx/Desktop/backups -l log_file.log -v -q2 /Users/spiceindeedx/Desktop/test_db test_text1

Query the database to display all log messages for all files from a certain directory. (The directory is a parameter to your script):

python3 backup.py -s /Users/spiceindeedx/Desktop/test_db  -d /Users/spiceindeedx/Desktop/backups -l query_log.log -v -q3 /Users/spiceindeedx/Desktop/test_db -dt 2023-01-01


Display job information 

Display log entries
python3 app.py -s /Users/spiceindeedx/Desktop/test_db  -d /Users/spiceindeedx/Desktop/backups -l log_file.log -v --display-job-info 1

With app as a gift you will receive centralised log api server. You can also use it with terminal. Examples of commands you can find below:

# Add a new system
curl -X POST -H "Content-Type: application/json" -d '{"name": "System7", "ip_address": "192.168.1.7"}' http://127.0.0.1:5000/systems

# Add a new log entry
curl -X POST -H "Content-Type: application/json" -d '{"system_name": "System4", "log_date": "2023-01-01", "log_level": "INFO", "message": "Log message", "directory": "/path/to/directory"}' http://127.0.0.1:5000/logs


#retrieve all logs
curl http://127.0.0.1:5000/logs

# retrieve log of a specific system
curl http://127.0.0.1:5000/logs/system/System1

# retrieve log of a specific system
curl http://127.0.0.1:5000/logs/date/2023-01-02

# delete logs before specific date
curl -X DELETE http://127.0.0.1:5000/logs/delete-before/2023-01-01

# update a log entry
curl -X PUT -H "Content-Type: application/json" -d '{"system": "UpdatedSystem", "log_level": "ERROR", "message": "Updated message", "directory": "/updated/directory"}' http://127.0.0.1:5000/logs/update/8


The apps were designed by Artem Tiutenko
