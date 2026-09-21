ALTER TABLE review_candidates
    ADD COLUMN reviewed_at TIMESTAMP(6) NULL;

ALTER TABLE review_candidates
    ADD COLUMN review_note ${lobType} NULL;
