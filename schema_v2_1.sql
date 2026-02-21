-- ================================================================
-- VICTORIAN NUMERACY LEARNING SEQUENCE
-- Schema v2.1 — Resource Types & File Storage Update
-- ================================================================
-- Changes from v2.0:
--   • Resource types updated to pedagogical categories:
--     Sandbox, Instructional Material, Guided Practice,
--     Independent Practice, Extension, Activity,
--     Retrieval Practice, Quiz
--   • Small files (PDF, DOC, images) stored as BLOB in database
--   • PPT/large files stored in /uploads folder, path in database
--   • audience field on resources: teacher / student / both
--   • file_format field added to capture actual file type
--     separately from pedagogical resource_type
-- ================================================================


-- ============================================================
-- REFERENCE / LOOKUP TABLES
-- ============================================================

CREATE TABLE year_levels (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(20)  NOT NULL UNIQUE,  -- 'F', 'Y1', 'Y2'...
    name          VARCHAR(50)  NOT NULL UNIQUE,  -- 'Foundation', 'Year 1'...
    display_order INTEGER      NOT NULL,
    description   TEXT
);

CREATE TABLE strands (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          VARCHAR(50)  NOT NULL UNIQUE,
    display_order INTEGER      NOT NULL,
    description   TEXT
);

CREATE TABLE cpa_stages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(10)  NOT NULL UNIQUE,  -- 'C','P','A','CP','PA','CPA'
    name          VARCHAR(50)  NOT NULL,
    display_order INTEGER      NOT NULL,
    description   TEXT
);

CREATE TABLE intrinsic_load_levels (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(10)  NOT NULL UNIQUE,  -- 'LOW','MEDIUM','HIGH'
    name          VARCHAR(20)  NOT NULL,
    display_order INTEGER      NOT NULL,
    description   TEXT
);

CREATE TABLE concept_stability_levels (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(10)  NOT NULL UNIQUE,
    name          VARCHAR(20)  NOT NULL,
    display_order INTEGER      NOT NULL,
    description   TEXT
);

-- ----------------------------------------------------------------
-- Pedagogical resource categories — what the resource IS FOR
-- Separate from file format (PDF, PPTX, etc.)
-- ----------------------------------------------------------------
CREATE TABLE resource_categories (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(30)  NOT NULL UNIQUE,
    name          VARCHAR(60)  NOT NULL,
    icon          VARCHAR(10),
    description   TEXT,
    display_order INTEGER      NOT NULL,

    -- Typical expected file formats for this category (informational)
    typical_formats TEXT   -- e.g. 'PDF, DOC' — just a hint, not enforced
);

-- ----------------------------------------------------------------
-- File formats — what the file actually IS
-- Separate from pedagogical category
-- ----------------------------------------------------------------
CREATE TABLE file_formats (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(10)  NOT NULL UNIQUE,  -- 'PDF','DOC','PPTX','IMG','OTHER'
    name          VARCHAR(50)  NOT NULL,
    mime_types    TEXT,        -- comma-separated list of valid MIME types
    stored_in_db  BOOLEAN      NOT NULL DEFAULT 1,  -- 1=BLOB in db, 0=file path only
    icon          VARCHAR(10)
);


-- ============================================================
-- CORE CONTENT TABLES
-- ============================================================

CREATE TABLE clusters (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_number INTEGER      NOT NULL UNIQUE,
    title          VARCHAR(255) NOT NULL,
    year_level_id  INTEGER      NOT NULL,
    strand_id      INTEGER,

    -- Learning design
    rationale      TEXT,        -- WHY these elements belong together cognitively
    sequence_notes TEXT,        -- notes on internal ordering of elements

    -- Metadata
    is_published   BOOLEAN      DEFAULT 0,
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (year_level_id) REFERENCES year_levels(id),
    FOREIGN KEY (strand_id)     REFERENCES strands(id)
);

-- ----------------------------------------------------------------
-- Victorian Curriculum 2.0 references
-- A cluster can align to one or more VC2.0 content descriptions.
-- Each reference has:
--   code        — e.g. VC2MFN02   (structured: VC2 + M + level + strand + num)
--   description — the full content description text from the VCAA site
--   url         — direct link to f10.vcaa.vic.edu.au content description page
-- ----------------------------------------------------------------
CREATE TABLE vc_references (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id     INTEGER      NOT NULL,

    code           VARCHAR(20)  NOT NULL,   -- e.g. VC2MFN02
    description    TEXT         NOT NULL,   -- full content description text
    url            TEXT         NOT NULL,   -- https://f10.vcaa.vic.edu.au/...

    -- Metadata
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (cluster_id) REFERENCES clusters(id) ON DELETE CASCADE,

    -- A cluster shouldn't reference the same VC code twice
    UNIQUE (cluster_id, code)
);

CREATE TABLE elements (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    element_number   INTEGER      NOT NULL UNIQUE,
    title            VARCHAR(255) NOT NULL,

    -- Learning design
    learning_objective   TEXT,
    teacher_notes        TEXT,
    intrinsic_load_id    INTEGER,
    concept_stability_id INTEGER,
    cpa_stage_id         INTEGER,
    audio_script         TEXT,

    -- Metadata
    is_published     BOOLEAN      DEFAULT 0,
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (intrinsic_load_id) REFERENCES intrinsic_load_levels(id),
    FOREIGN KEY (concept_stability_id) REFERENCES concept_stability_levels(id),
    FOREIGN KEY (cpa_stage_id)      REFERENCES cpa_stages(id)
);


-- ============================================================
-- RELATIONSHIP TABLES
-- ============================================================

-- Elements ↔ Clusters  (many-to-many, supports bridging elements)
CREATE TABLE cluster_elements (
    cluster_id     INTEGER NOT NULL,
    element_id     INTEGER NOT NULL,
    sequence_order INTEGER NOT NULL DEFAULT 0,
    is_bridging    BOOLEAN          DEFAULT 0,
    bridging_note  TEXT,

    PRIMARY KEY (cluster_id, element_id),
    FOREIGN KEY (cluster_id) REFERENCES clusters(id) ON DELETE CASCADE,
    FOREIGN KEY (element_id) REFERENCES elements(id) ON DELETE CASCADE
);

-- Element prerequisites  (self-referential many-to-many)
CREATE TABLE element_prerequisites (
    element_id        INTEGER NOT NULL,   -- element that HAS a prerequisite
    prerequisite_id   INTEGER NOT NULL,   -- element that must come FIRST
    relationship_note TEXT,

    PRIMARY KEY (element_id, prerequisite_id),
    FOREIGN KEY (element_id)      REFERENCES elements(id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_id) REFERENCES elements(id) ON DELETE CASCADE,
    CHECK (element_id != prerequisite_id)
);

-- ----------------------------------------------------------------
-- Resources  (1 resource → 1 element, always)
--
-- Storage strategy:
--   • PDF, DOC, images → file_data BLOB (stored directly in DB)
--   • PPTX             → file_data NULL, file_path set (folder reference)
--
-- The file_format_id tells the app which strategy to use.
-- ----------------------------------------------------------------
CREATE TABLE resources (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    element_id           INTEGER      NOT NULL,
    resource_category_id INTEGER      NOT NULL,  -- pedagogical: what it's FOR
    file_format_id       INTEGER      NOT NULL,  -- technical: what it IS

    title                VARCHAR(255) NOT NULL,
    description          TEXT,
    audience             VARCHAR(10)  NOT NULL DEFAULT 'both'
                             CHECK(audience IN ('teacher','student','both')),

    -- For PDF / DOC / images — file stored directly in the database
    file_data            BLOB,        -- binary file content

    -- For PPTX — file stored in /uploads folder, path recorded here
    file_path            TEXT,        -- e.g. 'uploads/elem_101/lesson_1.pptx'
    file_name            TEXT,        -- original filename
    file_size_bytes      INTEGER,
    mime_type            TEXT,

    -- Metadata
    uploaded_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (element_id)           REFERENCES elements(id) ON DELETE CASCADE,
    FOREIGN KEY (resource_category_id) REFERENCES resource_categories(id),
    FOREIGN KEY (file_format_id)       REFERENCES file_formats(id)
);


-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_clusters_year         ON clusters(year_level_id);
CREATE INDEX idx_clusters_strand       ON clusters(strand_id);
CREATE INDEX idx_vc_refs_cluster       ON vc_references(cluster_id);
CREATE INDEX idx_vc_refs_code          ON vc_references(code);
CREATE INDEX idx_cluster_elements_seq  ON cluster_elements(cluster_id, sequence_order);
CREATE INDEX idx_elements_load         ON elements(intrinsic_load_id);
CREATE INDEX idx_elements_concept_stability ON elements(concept_stability_id);
CREATE INDEX idx_elements_cpa          ON elements(cpa_stage_id);
CREATE INDEX idx_prereqs_element       ON element_prerequisites(element_id);
CREATE INDEX idx_prereqs_prereq        ON element_prerequisites(prerequisite_id);
CREATE INDEX idx_resources_element     ON resources(element_id);
CREATE INDEX idx_resources_category    ON resources(resource_category_id);
CREATE INDEX idx_resources_audience    ON resources(audience);


-- ============================================================
-- VIEWS
-- ============================================================

CREATE VIEW v_clusters AS
SELECT
    c.id, c.cluster_number, c.title,
    yl.code  AS year_level_code,
    yl.name  AS year_level,
    s.name   AS strand,
    c.rationale, c.sequence_notes, c.is_published,
    COUNT(DISTINCT ce.element_id)  AS element_count,
    COUNT(DISTINCT vc.id)          AS vc_reference_count,
    GROUP_CONCAT(DISTINCT vc.code) AS vc_codes
FROM clusters c
JOIN  year_levels yl          ON c.year_level_id = yl.id
LEFT JOIN strands s           ON c.strand_id = s.id
LEFT JOIN cluster_elements ce ON ce.cluster_id = c.id
LEFT JOIN vc_references vc    ON vc.cluster_id = c.id
GROUP BY c.id;

-- VC references view — full detail per reference
CREATE VIEW v_vc_references AS
SELECT
    vc.id, vc.cluster_id,
    c.cluster_number, c.title AS cluster_title,
    yl.name AS year_level,
    vc.code, vc.description, vc.url
FROM vc_references vc
JOIN clusters c    ON vc.cluster_id = c.id
JOIN year_levels yl ON c.year_level_id = yl.id
ORDER BY c.cluster_number, vc.code;

CREATE VIEW v_elements AS
SELECT
    e.id, e.element_number, e.title,
    e.learning_objective, e.teacher_notes,
    ill.code AS intrinsic_load,
    csl.code AS concept_stability,
    cpa.code AS cpa_stage,
    e.is_published,
    COUNT(DISTINCT ep.prerequisite_id) AS prerequisite_count,
    COUNT(DISTINCT r.id)               AS resource_count
FROM elements e
LEFT JOIN intrinsic_load_levels ill ON e.intrinsic_load_id = ill.id
LEFT JOIN concept_stability_levels csl ON e.concept_stability_id = csl.id
LEFT JOIN cpa_stages cpa            ON e.cpa_stage_id = cpa.id
LEFT JOIN element_prerequisites ep  ON ep.element_id = e.id
LEFT JOIN resources r               ON r.element_id = e.id
GROUP BY e.id;

CREATE VIEW v_prerequisite_chains AS
SELECT
    e.element_number AS element_num,   e.title AS element_title,
    p.element_number AS requires_num,  p.title AS requires_title,
    ep.relationship_note
FROM element_prerequisites ep
JOIN elements e ON ep.element_id      = e.id
JOIN elements p ON ep.prerequisite_id = p.id;

CREATE VIEW v_bridging_elements AS
SELECT
    e.element_number, e.title,
    COUNT(ce.cluster_id) AS appears_in_clusters,
    GROUP_CONCAT(c.title, ' | ') AS cluster_names
FROM elements e
JOIN cluster_elements ce ON ce.element_id = e.id
JOIN clusters c          ON c.id = ce.cluster_id
GROUP BY e.id
HAVING COUNT(ce.cluster_id) > 1;

-- Resources view — excludes binary blob, safe for listings
CREATE VIEW v_resources AS
SELECT
    r.id, r.element_id, r.title, r.description, r.audience,
    rc.name  AS category,
    rc.icon  AS category_icon,
    ff.code  AS file_format,
    ff.icon  AS format_icon,
    r.file_name, r.file_size_bytes, r.mime_type,
    r.file_path,
    CASE WHEN r.file_data IS NOT NULL THEN 1 ELSE 0 END AS stored_in_db,
    r.uploaded_at
FROM resources r
JOIN resource_categories rc ON r.resource_category_id = rc.id
JOIN file_formats ff        ON r.file_format_id = ff.id;


-- ============================================================
-- SEED DATA
-- ============================================================

INSERT INTO year_levels (code, name, display_order) VALUES
    ('F',  'Foundation', 0),
    ('Y1', 'Year 1',     1),
    ('Y2', 'Year 2',     2),
    ('Y3', 'Year 3',     3),
    ('Y4', 'Year 4',     4),
    ('Y5', 'Year 5',     5),
    ('Y6', 'Year 6',     6);

INSERT INTO strands (name, display_order) VALUES
    ('Number',      1),
    ('Algebra',     2),
    ('Measurement', 3),
    ('Space',       4),
    ('Statistics',  5);

INSERT INTO cpa_stages (code, name, display_order, description) VALUES
    ('C',   'Concrete',                       1, 'Physical manipulation of objects'),
    ('P',   'Pictorial',                      2, 'Visual representations and diagrams'),
    ('A',   'Abstract',                       3, 'Symbolic and numerical notation'),
    ('CP',  'Concrete → Pictorial',           4, 'Transitioning from concrete to pictorial'),
    ('PA',  'Pictorial → Abstract',           5, 'Transitioning from pictorial to abstract'),
    ('CPA', 'Concrete → Pictorial → Abstract',6, 'Full progression through all stages');

INSERT INTO intrinsic_load_levels (code, name, display_order, description) VALUES
    ('LOW',    'Low',    1, 'Single concept, minimal interacting elements, accessible to most students at this level'),
    ('MEDIUM', 'Medium', 2, 'Two or three interacting concepts, requires solid prior knowledge'),
    ('HIGH',   'High',   3, 'Multiple interacting concepts, high element interactivity, demands strong prior knowledge');

INSERT INTO concept_stability_levels (code, name, display_order, description) VALUES
    ('LOW',    'Low',    1, 'Concept consolidates relatively readily; minimal reiteration needed'),
    ('MEDIUM', 'Medium', 2, 'Moderate reiteration and retrieval practice needed for consolidation'),
    ('HIGH',   'High',   3, 'Concept is fragile; requires lots of revisiting and retrieval to consolidate');

-- Pedagogical resource categories
INSERT INTO resource_categories (code, name, icon, display_order, description, typical_formats) VALUES
    ('SANDBOX',        'Sandbox',               '🧪', 1, 'Interactive exploration activity — open-ended, student-led',          'Interactive/web'),
    ('INSTRUCTIONAL',  'Instructional Material', '📖', 2, 'Teacher-facing material for delivering the lesson',                  'PDF, PPTX, DOC'),
    ('GUIDED',         'Guided Practice',        '🤝', 3, 'Structured practice with teacher support',                           'PDF, DOC'),
    ('INDEPENDENT',    'Independent Practice',   '✏️', 4, 'Student works independently to consolidate learning',                'PDF, DOC'),
    ('EXTENSION',      'Extension',              '🚀', 5, 'Stretch material for students who are ready to go further',          'PDF, DOC'),
    ('ACTIVITY',       'Activity',               '🎯', 6, 'Hands-on or game-based learning activity',                          'PDF, DOC, IMG'),
    ('RETRIEVAL',      'Retrieval Practice',     '🔁', 7, 'Low-stakes retrieval to strengthen memory of prior learning',        'PDF, DOC'),
    ('QUIZ',           'Quiz',                   '✅', 8, 'Formative assessment to check understanding',                        'PDF, DOC');

-- File formats — controls storage strategy
INSERT INTO file_formats (code, name, mime_types, stored_in_db, icon) VALUES
    ('PDF',   'PDF Document',   'application/pdf',                                                    1, '📄'),
    ('DOC',   'Word Document',  'application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document', 1, '📝'),
    ('IMG',   'Image',          'image/png,image/jpeg,image/gif,image/webp',                          1, '🖼️'),
    ('PPTX',  'PowerPoint',     'application/vnd.openxmlformats-officedocument.presentationml.presentation', 0, '📊'),
    ('OTHER', 'Other',          '',                                                                   0, '📎');
