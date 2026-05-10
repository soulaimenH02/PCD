-- ============================================================
-- FarmWatch Bird Detection System — PostgreSQL Schema
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sectors / camera zones on the farm
CREATE TABLE sectors (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(10)  NOT NULL UNIQUE,  -- e.g. 'A', 'B', 'C'
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Cameras registered in the system
CREATE TABLE cameras (
    id          SERIAL PRIMARY KEY,
    sector_id   INT          NOT NULL REFERENCES sectors(id),
    name        VARCHAR(100) NOT NULL,
    stream_url  VARCHAR(500),               -- RTSP / MJPEG URL
    active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Every bird detection event
CREATE TABLE detections (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    sector_id       INT          NOT NULL REFERENCES sectors(id),
    camera_id       INT          REFERENCES cameras(id),
    detected_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    method          VARCHAR(20)  NOT NULL CHECK (method IN ('CAMERA','SOUND','BOTH')),
    confidence      NUMERIC(5,2) NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    species_est     VARCHAR(100),           -- estimated species from model
    duration_secs   INT,                    -- how long the bird was detected
    image_path      VARCHAR(500),           -- snapshot path if camera
    audio_path      VARCHAR(500),           -- audio clip path if sound
    siren_triggered BOOLEAN      NOT NULL DEFAULT FALSE,
    notes           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Siren activation log (manual + automatic)
CREATE TABLE siren_events (
    id              SERIAL       PRIMARY KEY,
    detection_id    UUID         REFERENCES detections(id),
    triggered_by    VARCHAR(20)  NOT NULL CHECK (triggered_by IN ('AUTO','MANUAL')),
    triggered_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    stopped_at      TIMESTAMPTZ,
    duration_secs   INT GENERATED ALWAYS AS
                    (EXTRACT(EPOCH FROM (stopped_at - triggered_at))::INT) STORED,
    triggered_by_user VARCHAR(100)  -- username if manual
);

-- System configuration (key-value store)
CREATE TABLE system_config (
    key         VARCHAR(100) PRIMARY KEY,
    value       TEXT         NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── Indexes ────────────────────────────────────────────────
CREATE INDEX idx_detections_detected_at  ON detections(detected_at DESC);
CREATE INDEX idx_detections_sector       ON detections(sector_id);
CREATE INDEX idx_detections_method       ON detections(method);
CREATE INDEX idx_siren_events_triggered  ON siren_events(triggered_at DESC);

-- ── Seed data ──────────────────────────────────────────────
INSERT INTO sectors (code, name, description) VALUES
    ('A', 'Sector A – North Field',  'Main crop area, north side'),
    ('B', 'Sector B – East Field',   'Secondary crop rows, east side'),
    ('C', 'Sector C – Storage Zone', 'Grain storage and silos');

INSERT INTO cameras (sector_id, name, stream_url) VALUES
    (1, 'CAM-01 North',    'rtsp://192.168.1.101:554/stream'),
    (2, 'CAM-02 East',     'rtsp://192.168.1.102:554/stream'),
    (3, 'CAM-03 Storage',  'rtsp://192.168.1.103:554/stream');

INSERT INTO system_config (key, value, description) VALUES
    ('siren.mode',                   'AUTO',   'AUTO | MANUAL | DISABLED'),
    ('siren.auto_threshold',         '80',     'Confidence % to auto-trigger siren'),
    ('siren.auto_duration_secs',     '10',     'How long auto siren stays on'),
    ('detection.camera_enabled',     'true',   'Enable camera-based detection'),
    ('detection.sound_enabled',      'true',   'Enable sound-based detection');
