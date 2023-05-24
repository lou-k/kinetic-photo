
CREATE TABLE integrations (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    params TEXT NOT NULL
);

-- CREATE TABLE kinetic.filters (
--     id INTEGER PRIMARY KEY,
--     source_id INTEGER,
--     params TEXT NOT NULL
--     FOREIGN KEY (source_id)
--         REFERENCES sources (id)
--         ON DELETE CASCADE
--         ON UPDATE NO ACTION
-- );

-- CREATE TABLE kinetic.processors (
--     id INTEGER PRIMARY KEY,
--     name TEXT NOT NULL,
--     params TEXT NOT NULL
-- );

-- CREATE TABLE kinetic.processor_filters (
--     processor_id INTEGER,
--     filter_id INTEGER,
--     PRIMARY KEY (processor_id, filter_id)
--     FOREIGN KEY (processor_id)
--         REFERENCES processors (id)
--         ON DELETE CASCADE
--         ON UPDATE NO ACTION
--     FOREIGN KEY (filter_id)
--         REFERENCES filters (id)
--         ON DELETE CASCADE
--         ON UPDATE NO ACTION
-- );

-- CREATE TABLE kinetic.content (
--     id INTEGER PRIMARY KEY,
--     added_on TEXT NOT NULL,
--     object_hash TEXT NOT NULL,
--     source_id INTEGER,
--     processor_id INTEGER,
--     source_object_identifier TEXT NOT NULL,
--     metadata TEXT,
--     FOREIGN KEY (processor_id)
--         REFERENCES processors (id)
--         ON DELETE SET NULL
--         ON UPDATE NO ACTION
--     FOREIGN KEY (source_id)
--         REFERENCES sources (id)
--         ON DELETE SET NULL
--         ON UPDATE NO ACTION
-- );

-- CREATE TABLE kinetic.frames (
--     id INTEGER PRIMARY KEY,
--     name TEXT NOT NULL,
--     content_filter TEXT NOT NULL
-- );