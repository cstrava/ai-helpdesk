ALTER TABLE tickets ADD COLUMN impact TEXT CHECK (impact IS NULL OR impact IN ('individual','team','organization'));
CREATE TABLE notifications (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 recipient_id UUID NOT NULL REFERENCES users(id),
 ticket_id UUID NOT NULL REFERENCES tickets(id),
 kind TEXT NOT NULL CHECK(kind IN ('reply','assignment','status')),
 source_key UUID NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 read_at TIMESTAMPTZ,
 UNIQUE(recipient_id,ticket_id,kind,source_key)
);
CREATE INDEX notifications_recipient_page ON notifications(recipient_id,created_at DESC,id DESC);
CREATE INDEX tickets_priority_page ON tickets(priority,created_at DESC,id DESC);
