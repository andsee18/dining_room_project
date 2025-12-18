CREATE TABLE IF NOT EXISTS visit_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    entered INT NOT NULL,
    exited INT NOT NULL,
    people_inside INT NOT NULL,
    occupied_tables INT NOT NULL,
    free_tables INT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_reports (
    date DATE PRIMARY KEY,
    entered_total INT NOT NULL,
    exited_total INT NOT NULL,
    max_inside INT NOT NULL,
    min_inside INT NOT NULL
);