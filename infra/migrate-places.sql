-- Run once on existing Cloud SQL instances
ALTER TABLE matched_rates ADD COLUMN IF NOT EXISTS place_id VARCHAR(255);
ALTER TABLE matched_rates ADD COLUMN IF NOT EXISTS place_description TEXT;
