ALTER TABLE content
ADD COLUMN versions text;

UPDATE content SET versions=json_object("original", id, "faded", faded_hash) WHERE faded_hash IS NOT NULL;

UPDATE content SET versions=json_object("original", id) WHERE faded_hash IS NULL;

ALTER TABLE content DROP COLUMN faded_hash;