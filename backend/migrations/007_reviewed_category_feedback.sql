CREATE TABLE ticket_category_reviews (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 ticket_id UUID NOT NULL REFERENCES tickets(id),
 reviewer_id UUID NOT NULL REFERENCES users(id),
 request_id UUID NOT NULL,
 verified_category TEXT NOT NULL CHECK (verified_category IN (
  'Access','Administrative rights','HR Support','Hardware',
  'Internal Project','Miscellaneous','Purchase','Storage'
 )),
 model_version TEXT NOT NULL,
 text_sha256 CHAR(64) NOT NULL CHECK (text_sha256 ~ '^[0-9a-f]{64}$'),
 reason TEXT CHECK (reason IS NULL OR char_length(btrim(reason)) <= 1000),
 reviewed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 invalidated_at TIMESTAMPTZ,
 UNIQUE(ticket_id,reviewer_id,request_id)
);
CREATE INDEX ticket_category_reviews_approved
 ON ticket_category_reviews(reviewed_at,id) WHERE invalidated_at IS NULL;

CREATE FUNCTION invalidate_ticket_category_reviews() RETURNS trigger AS $$
BEGIN
 IF NEW.title IS DISTINCT FROM OLD.title
    OR NEW.text IS DISTINCT FROM OLD.text
    OR NEW.final_category IS DISTINCT FROM OLD.final_category THEN
  UPDATE ticket_category_reviews
  SET invalidated_at=clock_timestamp()
  WHERE ticket_id=NEW.id AND invalidated_at IS NULL;
 END IF;
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tickets_invalidate_category_review
 AFTER UPDATE OF title,text,final_category ON tickets
 FOR EACH ROW EXECUTE FUNCTION invalidate_ticket_category_reviews();
