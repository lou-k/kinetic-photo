CREATE TABLE content (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    width int NOT NULL,
    height int NOT NULL,
    external_id TEXT,
    metadata TEXT,
    stream_id INTEGER,
    FOREIGN KEY (stream_id)
        REFERENCES streams (id)
        ON DELETE SET NULL
        ON UPDATE NO ACTION
);

-- Index on creation time so that we can quickly sort by date --
CREATE INDEX content_created_at_idx ON content (created_at);

-- Index on streams to make filtering fast if the user filters on those --
CREATE INDEX content_stream_id_idx ON content (stream_id);
