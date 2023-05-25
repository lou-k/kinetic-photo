CREATE TABLE streams (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    integration_id INTEGER,
    params_json TEXT,
    filters_json TEXT,
    FOREIGN KEY (integration_id)
         REFERENCES integrations (id)
         ON DELETE CASCADE
         ON UPDATE NO ACTION
);
