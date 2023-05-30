CREATE TABLE pipelines (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE pipeline_steps (
    id INTEGER PRIMARY KEY,
    pipeline_id INTEGER NOT NULL,
    rule Rule NOT NULL,
    processor Processor NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines (id) ON DELETE CASCADE ON UPDATE NO ACTION
);

CREATE TABLE pipeline_runs (
    id INTEGER PRIMARY KEY,
    pipeline_id INTEGER NOT NULL,
    log_hash TEXT NOT NULL,
    completed_at timestamp NOT NULL,
    status PipelineStatus NOT NULL,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines (id) ON DELETE CASCADE ON UPDATE NO ACTION
);

-- Index the pipeline runs by pipeline id and when it was run --
CREATE INDEX pipleine_recent_runs_idx ON pipeline_runs (pipeline_id, completed_at);