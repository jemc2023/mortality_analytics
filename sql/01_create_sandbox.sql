CREATE SCHEMA IF NOT EXISTS sandbox;

CREATE TABLE IF NOT EXISTS sandbox.defunciones_raw (
    id_sandbox          SERIAL PRIMARY KEY,
    source              VARCHAR(50)  NOT NULL,
    year                INTEGER,
    month               INTEGER,
    department          VARCHAR(100),
    municipality        VARCHAR(100),
    cause_icd10         VARCHAR(20),
    sex                 VARCHAR(10),
    age_group           VARCHAR(50),
    total_deaths        INTEGER,
    ingestion_ts        TIMESTAMP DEFAULT NOW(),
    source_file         VARCHAR(255),
    record_hash         VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_sandbox_source  ON sandbox.defunciones_raw(source);
CREATE INDEX IF NOT EXISTS idx_sandbox_year    ON sandbox.defunciones_raw(year);
CREATE INDEX IF NOT EXISTS idx_sandbox_cause   ON sandbox.defunciones_raw(cause_icd10);
