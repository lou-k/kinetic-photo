CREATE TABLE uploads (
    id TEXT PRIMARY KEY, -- the object hash of this file
    created_at timestamp, -- when the file was created, as extracted from the exif data
    uploaded_at timestamp, -- when the file was uploaded
    metadata TEXT, -- a json map of metadata about this file
    content_type TEXT -- what kind of file this is.
);

-- Index on creation time so that we can quickly sort by date --
CREATE INDEX uploads_created_at_idx ON uploads (created_at);
CREATE INDEX uploads_uploaded_at_idx ON uploads (uploaded_at);