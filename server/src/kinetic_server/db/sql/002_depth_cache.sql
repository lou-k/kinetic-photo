CREATE TABLE depth_cache (
    id TEXT PRIMARY KEY,
    -- the source id that the depth map was generated from
    extracted_at timestamp NOT NULL,
    -- when the depth was extracted from the source file
    depth_hash TEXT NOT NULL
    -- the hash of the depth image in the file store
);