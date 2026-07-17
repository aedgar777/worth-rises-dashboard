-- Cloud SQL schema for Worth Rises telecom matcher

CREATE TABLE IF NOT EXISTS uploads (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'processing',
    jurisdiction_count INTEGER DEFAULT 0,
    matched_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matched_rates (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    jurisdiction_type VARCHAR(20) NOT NULL,
    state VARCHAR(2) NOT NULL,
    county VARCHAR(100),
    facility_name VARCHAR(255),
    provider VARCHAR(100),
    in_state_rate DOUBLE PRECISION,
    out_of_state_rate DOUBLE PRECISION,
    match_status VARCHAR(50) NOT NULL,
    match_confidence DOUBLE PRECISION DEFAULT 0,
    notes TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    place_id VARCHAR(255),
    place_description TEXT
);

CREATE INDEX IF NOT EXISTS idx_matched_rates_upload_id ON matched_rates(upload_id);
CREATE INDEX IF NOT EXISTS idx_matched_rates_state ON matched_rates(state);
