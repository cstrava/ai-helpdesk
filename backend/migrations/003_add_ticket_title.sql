ALTER TABLE tickets
    ADD COLUMN title TEXT
    CHECK (
        title IS NULL
        OR (btrim(title) <> '' AND char_length(title) <= 160)
    );