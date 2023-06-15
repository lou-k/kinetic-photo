
CREATE TABLE pre_renders (
    id INTEGER PRIMARY KEY,
    frame_id TEXT NOT NULL,
    created_at timestamp NOT NULL,
    video_hash TEXT NOT NULL,
    video_ids TEXT NOT NULL,
    FOREIGN KEY (frame_id) REFERENCES frames (id) ON DELETE SET NULL ON UPDATE NO ACTION
);