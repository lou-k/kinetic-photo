-- Index on source id so that we can lookup content by external id quickly --
CREATE INDEX content_source_id_idx ON content (source_id);