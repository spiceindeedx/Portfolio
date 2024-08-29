CREATE TABLE IF NOT EXISTS system (
    system_id INTEGER PRIMARY KEY,
    name TEXT,
    ip_address TEXT
);

CREATE TABLE IF NOT EXISTS logs (
    log_id INTEGER PRIMARY KEY,
    system_id INTEGER,
    log_date TEXT NOT NULL,
    log_level TEXT NOT NULL,
    message TEXT NOT NULL,
    directory TEXT,
    FOREIGN KEY (system_id) REFERENCES system(system_id)
);
