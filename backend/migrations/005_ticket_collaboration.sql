ALTER TABLE tickets
 ADD COLUMN assignee_id UUID REFERENCES users(id),
 ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low','normal','high','urgent')),
 ADD COLUMN version INTEGER NOT NULL DEFAULT 0,
 ADD COLUMN updated_at TIMESTAMPTZ,
 ADD COLUMN first_resolved_at TIMESTAMPTZ;
ALTER TABLE tickets ALTER COLUMN updated_at SET DEFAULT now();
-- Only existing timestamped events provide evidence of a historical resolution.
UPDATE tickets t SET first_resolved_at = (
 SELECT min(e.created_at) FROM ticket_events e
 WHERE e.ticket_id=t.id AND e.field='status' AND e.new_value='resolved'
);
ALTER TABLE ticket_events DROP CONSTRAINT ticket_events_field_check;
ALTER TABLE ticket_events ADD CONSTRAINT ticket_events_field_check
 CHECK(field IN ('status','final_category','assignee_id','priority'));
CREATE TABLE ticket_messages (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 ticket_id UUID NOT NULL REFERENCES tickets(id),
 author_id UUID NOT NULL REFERENCES users(id),
 content TEXT NOT NULL CHECK (char_length(btrim(content)) BETWEEN 1 AND 4000),
 visibility TEXT NOT NULL CHECK (visibility IN ('public','internal')),
 kind TEXT NOT NULL CHECK (kind IN ('reply','resolution','reopen')),
 request_id UUID NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(ticket_id,author_id,request_id)
);
CREATE INDEX ON ticket_messages(ticket_id,created_at,id);
CREATE INDEX ON tickets(assignee_id,created_at DESC,id DESC);
