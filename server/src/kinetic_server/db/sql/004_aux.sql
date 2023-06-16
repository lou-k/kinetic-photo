CREATE TABLE auxiliary_cache (
    id TEXT,
    -- the identifier of the media this data was computed for
    computed_at timestamp NOT NULL,
    -- when this data was computed
    type TEXT NOT NULL,
    -- what kind of data this is
    file_hash TEXT,
    -- The object store has where this data are stored
    PRIMARY KEY (id, type)
);