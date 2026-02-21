-- Add concept_stability dimension to elements
-- Concept stability = how much reiteration/retrieval practice needed for consolidation
-- (Distinct from intrinsic load, which measures working-memory demand during learning)

-- Lookup table
CREATE TABLE concept_stability_levels (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(10)  NOT NULL UNIQUE,
    name          VARCHAR(20)  NOT NULL,
    display_order INTEGER      NOT NULL,
    description   TEXT
);

INSERT INTO concept_stability_levels (code, name, display_order, description) VALUES
    ('LOW',    'Low',    1, 'Concept consolidates relatively readily; minimal reiteration needed'),
    ('MEDIUM', 'Medium', 2, 'Moderate reiteration and retrieval practice needed for consolidation'),
    ('HIGH',   'High',   3, 'Concept is fragile; requires lots of revisiting and retrieval to consolidate');

-- Add column to elements
ALTER TABLE elements ADD COLUMN concept_stability_id INTEGER REFERENCES concept_stability_levels(id);

CREATE INDEX idx_elements_concept_stability ON elements(concept_stability_id);
