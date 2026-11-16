BEGIN;

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE conversation_messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL CHECK (btrim(content) <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversation_messages_conversation_id_id
    ON conversation_messages (conversation_id, id);

ALTER TABLE tickets
    ADD COLUMN conversation_id UUID REFERENCES conversations(id),
    ADD CONSTRAINT tickets_conversation_id_unique UNIQUE (conversation_id);

COMMIT;