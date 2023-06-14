CREATE TABLE integrations (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    params TEXT NOT NULL
);

CREATE TABLE streams (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    integration_id INTEGER,
    params_json TEXT,
    FOREIGN KEY (integration_id) REFERENCES integrations (id) ON DELETE CASCADE ON UPDATE NO ACTION
);

CREATE TABLE pipelines (
    id INTEGER PRIMARY KEY,
    stream_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (stream_id) REFERENCES streams (id) ON DELETE
    SET
        NULL ON UPDATE NO ACTION
);

CREATE INDEX pipelines_stream_id_idx ON pipelines (stream_id);

CREATE TABLE content (
    id TEXT PRIMARY KEY,
    created_at timestamp,
    height int,
    metadata TEXT,
    pipeline_id INTEGER,
    processed_at timestamp,
    source_id TEXT,
    stream_id INTEGER,
    width int,
    versions text,
    FOREIGN KEY (stream_id) REFERENCES streams (id) ON DELETE
    SET
        NULL ON UPDATE NO ACTION,
        FOREIGN KEY (pipeline_id) REFERENCES pipelines (id) ON DELETE
    SET
        NULL ON UPDATE NO ACTION
);

CREATE INDEX content_created_at_idx ON content (created_at);

CREATE INDEX content_stream_id_idx ON content (stream_id);

CREATE INDEX content_pipeline_id_idx ON content (pipeline_id);

CREATE INDEX content_source_id_idx ON content (source_id);

CREATE TABLE pipeline_steps (
    id INTEGER PRIMARY KEY,
    pipeline_id INTEGER NOT NULL,
    step Step NOT NULL,
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

CREATE INDEX pipleine_recent_runs_idx ON pipeline_runs (pipeline_id, completed_at);

CREATE TABLE frames (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    options TEXT NOT NULL
);

CREATE TABLE uploads (
    id TEXT PRIMARY KEY,
    -- the object hash of this file
    created_at timestamp,
    -- when the file was created, as extracted from the exif data
    uploaded_at timestamp,
    -- when the file was uploaded
    metadata TEXT,
    -- a json map of metadata about this file
    content_type TEXT -- what kind of file this is.
);

CREATE INDEX uploads_created_at_idx ON uploads (created_at);

CREATE INDEX uploads_uploaded_at_idx ON uploads (uploaded_at);