CREATE TABLE competitions (
    id VARCHAR(120) NOT NULL,
    active BOOLEAN NULL,
    brand_id VARCHAR(120) NULL,
    competition_end DATE NULL,
    competition_start DATE NULL,
    description ${lobType} NULL,
    display_order INT NOT NULL,
    edition VARCHAR(80) NULL,
    eligibility ${lobType} NULL,
    has_campus_notice BOOLEAN NULL,
    info_channel VARCHAR(120) NULL,
    kind VARCHAR(80) NULL,
    last_checked DATE NULL,
    level VARCHAR(80) NULL,
    link VARCHAR(1000) NULL,
    link_kind VARCHAR(80) NULL,
    name VARCHAR(300) NOT NULL,
    needs_review BOOLEAN NULL,
    organizer VARCHAR(300) NULL,
    published_at DATE NULL,
    registration_end DATE NULL,
    registration_end_estimated DATE NULL,
    registration_start DATE NULL,
    registration_start_estimated DATE NULL,
    schedule_confidence VARCHAR(80) NULL,
    schedule_source VARCHAR(80) NULL,
    status_override VARCHAR(80) NULL,
    track_id VARCHAR(160) NULL,
    PRIMARY KEY (id)
);

CREATE TABLE competition_categories (
    competition_id VARCHAR(120) NOT NULL,
    category VARCHAR(120) NULL,
    item_order INT NOT NULL,
    PRIMARY KEY (competition_id, item_order),
    CONSTRAINT fk_competition_categories_competition
        FOREIGN KEY (competition_id) REFERENCES competitions (id)
);

CREATE TABLE competition_tags (
    competition_id VARCHAR(120) NOT NULL,
    tag VARCHAR(120) NULL,
    item_order INT NOT NULL,
    PRIMARY KEY (competition_id, item_order),
    CONSTRAINT fk_competition_tags_competition
        FOREIGN KEY (competition_id) REFERENCES competitions (id)
);
