CREATE TABLE review_candidates (
    id VARCHAR(180) NOT NULL,
    name VARCHAR(300) NOT NULL,
    link VARCHAR(1000) NULL,
    source VARCHAR(120) NULL,
    source_name VARCHAR(200) NULL,
    ai_verdict VARCHAR(40) NULL,
    ai_confidence VARCHAR(40) NULL,
    ai_reason ${lobType} NULL,
    review_status VARCHAR(20) NOT NULL,
    raw_data ${lobType} NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX idx_review_candidates_status
    ON review_candidates (review_status);

CREATE INDEX idx_review_candidates_updated_at
    ON review_candidates (updated_at);
