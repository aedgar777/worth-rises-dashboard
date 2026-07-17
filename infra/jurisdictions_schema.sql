-- Jurisdictions reference database (worth_rises_jurisdictions)

CREATE TABLE IF NOT EXISTS jurisdictions (
    id SERIAL PRIMARY KEY,
    jurisdiction_type VARCHAR(20) NOT NULL,
    state VARCHAR(2) NOT NULL,
    county VARCHAR(100),
    CONSTRAINT uq_jurisdiction UNIQUE (jurisdiction_type, state, county)
);

CREATE INDEX IF NOT EXISTS idx_jurisdictions_state ON jurisdictions(state);
CREATE INDEX IF NOT EXISTS idx_jurisdictions_type ON jurisdictions(jurisdiction_type);
