CREATE TABLE users (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 email TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('user','support')) DEFAULT 'user',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE sessions (
 token_hash TEXT PRIMARY KEY,
 user_id UUID NOT NULL REFERENCES users(id),
 csrf_token TEXT NOT NULL,
 expires_at TIMESTAMPTZ NOT NULL
);
ALTER TABLE conversations ADD COLUMN owner_id UUID REFERENCES users(id);
ALTER TABLE tickets ADD COLUMN owner_id UUID REFERENCES users(id);
CREATE INDEX ON conversations(owner_id, created_at DESC, id DESC);
CREATE INDEX ON tickets(owner_id, created_at DESC, id DESC);
CREATE TABLE ticket_events (
 id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 ticket_id UUID NOT NULL REFERENCES tickets(id),
 actor_id UUID NOT NULL REFERENCES users(id),
 field TEXT NOT NULL CHECK(field IN ('status','final_category')),
 old_value TEXT NOT NULL,
 new_value TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE auth_rate_limits (key TEXT PRIMARY KEY, attempts INTEGER NOT NULL, window_start TIMESTAMPTZ NOT NULL DEFAULT now());
