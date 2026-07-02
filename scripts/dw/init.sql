SELECT 'CREATE DATABASE dw_semis2'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'dw_semis2')\gexec

\c dw_semis2;

CREATE SCHEMA IF NOT EXISTS dm_mortality;
CREATE SCHEMA IF NOT EXISTS dm_stage;
CREATE SCHEMA IF NOT EXISTS dm_meta;

CREATE TABLE IF NOT EXISTS dm_mortality.dim_causa (
    id_causa BIGINT NOT NULL,
    cie10_code VARCHAR(32),
    cie10_nombre TEXT,
    gbd_code VARCHAR(64),
    gbd_nombre TEXT,
    icd10_group VARCHAR(255),
    source_system VARCHAR(128),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_causa)
)
DISTRIBUTED BY (id_causa);

CREATE TABLE IF NOT EXISTS dm_mortality.dim_etario (
    id_etario BIGINT NOT NULL,
    grupo_edad_codigo VARCHAR(64),
    grupo_edad VARCHAR(128),
    categoria_etaria VARCHAR(128),
    edad_minima INT,
    edad_maxima INT,
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_etario)
)
DISTRIBUTED BY (id_etario);

CREATE TABLE IF NOT EXISTS dm_mortality.dim_genero (
    id_genero BIGINT NOT NULL,
    sexo_codigo VARCHAR(32),
    sexo_nombre VARCHAR(64),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_genero)
)
DISTRIBUTED BY (id_genero);

CREATE TABLE IF NOT EXISTS dm_mortality.dim_geografia (
    id_geografia BIGINT NOT NULL,
    pais_iso3 CHAR(3),
    pais_nombre VARCHAR(128),
    dep_ocurrencia VARCHAR(128),
    mun_ocurrencia VARCHAR(128),
    lugar_defuncion VARCHAR(255),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_geografia)
)
DISTRIBUTED BY (id_geografia);

CREATE TABLE IF NOT EXISTS dm_mortality.dim_ihme_perfil (
    id_ihme_perfil BIGINT NOT NULL,
    metrica VARCHAR(64),
    medida VARCHAR(64),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ihme_perfil)
)
DISTRIBUTED BY (id_ihme_perfil);

CREATE TABLE IF NOT EXISTS dm_mortality.dim_ine_perfil (
    id_ine_perfil BIGINT NOT NULL,
    estado_civil VARCHAR(128),
    escolaridad VARCHAR(128),
    asistencia_medica VARCHAR(128),
    tipo_ocurrencia VARCHAR(128),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_ine_perfil)
)
DISTRIBUTED BY (id_ine_perfil);

CREATE TABLE IF NOT EXISTS dm_mortality.dim_source (
    id_source BIGINT NOT NULL,
    source VARCHAR(128),
    source_file TEXT,
    source_url TEXT,
    ingestion_ts TIMESTAMP,
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_source)
)
DISTRIBUTED BY (id_source);

CREATE TABLE IF NOT EXISTS dm_mortality.dim_tiempo (
    id_tiempo BIGINT NOT NULL,
    mes_ocurrencia VARCHAR(32),
    mes_ocurrencia_num INT,
    anio_ocurrencia INT,
    semana_epidemiologica INT,
    es_pre_covid BOOLEAN,
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_tiempo)
)
DISTRIBUTED BY (id_tiempo);

CREATE TABLE IF NOT EXISTS dm_mortality.fact_ihme (
    id_geografia BIGINT NOT NULL,
    id_genero BIGINT NOT NULL,
    id_causa BIGINT NOT NULL,
    id_tiempo BIGINT NOT NULL,
    id_source BIGINT NOT NULL,
    id_ihme_perfil BIGINT NOT NULL,
    valor NUMERIC(18, 6),
    limite_inferior NUMERIC(18, 6),
    limite_superior NUMERIC(18, 6),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTRIBUTED BY (id_tiempo);

CREATE TABLE IF NOT EXISTS dm_mortality.fact_ine (
    id_geografia BIGINT NOT NULL,
    id_tiempo BIGINT NOT NULL,
    id_source BIGINT NOT NULL,
    id_causa BIGINT NOT NULL,
    id_etario BIGINT NOT NULL,
    id_genero BIGINT NOT NULL,
    id_ine_perfil BIGINT NOT NULL,
    defuncion NUMERIC(18, 2),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTRIBUTED BY (id_tiempo);

CREATE TABLE IF NOT EXISTS dm_mortality.fact_mspas (
    id_geografia BIGINT NOT NULL,
    id_source BIGINT NOT NULL,
    id_tiempo BIGINT NOT NULL,
    defunciones NUMERIC(18, 2),
    tasa_por_100k NUMERIC(18, 6),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTRIBUTED BY (id_tiempo);

CREATE TABLE IF NOT EXISTS dm_mortality.fact_panama (
    id_etario BIGINT NOT NULL,
    id_causa BIGINT NOT NULL,
    id_genero BIGINT NOT NULL,
    id_source BIGINT NOT NULL,
    id_tiempo BIGINT NOT NULL,
    id_geografia BIGINT NOT NULL,
    defunciones NUMERIC(18, 2),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTRIBUTED BY (id_tiempo);

CREATE TABLE IF NOT EXISTS dm_mortality.fact_who_deaths (
    id_source BIGINT NOT NULL,
    id_geografia BIGINT NOT NULL,
    id_causa BIGINT NOT NULL,
    id_tiempo BIGINT NOT NULL,
    id_genero BIGINT NOT NULL,
    number NUMERIC(18, 2),
    prc_cause_specific_deaths_out_of_total_deaths NUMERIC(9, 6),
    age_std_death_rate_per_100k_std_population NUMERIC(18, 6),
    death_rate_per_100k_population NUMERIC(18, 6),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTRIBUTED BY (id_tiempo);

CREATE TABLE IF NOT EXISTS dm_mortality.fact_who_population (
    id_source BIGINT NOT NULL,
    id_tiempo BIGINT NOT NULL,
    id_geografia BIGINT NOT NULL,
    id_genero BIGINT NOT NULL,
    id_etario BIGINT NOT NULL,
    population NUMERIC(18, 2),
    record_hash CHAR(64),
    replicated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
DISTRIBUTED BY (id_tiempo);

CREATE TABLE IF NOT EXISTS dm_meta.replication_runs (
    run_id BIGSERIAL,
    source_system VARCHAR(64) NOT NULL DEFAULT 'databricks',
    target_system VARCHAR(64) NOT NULL DEFAULT 'greenplum',
    status VARCHAR(32) NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    error_message TEXT
)
DISTRIBUTED BY (run_id);

CREATE TABLE IF NOT EXISTS dm_meta.replication_table_checks (
    check_id BIGSERIAL,
    run_id BIGINT NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    databricks_row_count BIGINT,
    greenplum_row_count BIGINT,
    status VARCHAR(32) NOT NULL,
    checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
)
DISTRIBUTED BY (check_id);

CREATE TABLE IF NOT EXISTS dm_meta.backup_runs (
    backup_id BIGSERIAL,
    status VARCHAR(32) NOT NULL,
    backup_file TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    file_size_bytes BIGINT,
    error_message TEXT
)
DISTRIBUTED BY (backup_id);

CREATE TABLE IF NOT EXISTS dm_meta.processed_pipeline_runs (
    run_id VARCHAR(255) NOT NULL,
    pipeline_name VARCHAR(255) NOT NULL,
    databricks_completed_at TIMESTAMP,
    replication_status VARCHAR(32) NOT NULL,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_attempt_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    replicated_at TIMESTAMP,
    attempt_count INT NOT NULL DEFAULT 0,
    error_message TEXT,
    notes TEXT,
    PRIMARY KEY (run_id)
)
DISTRIBUTED BY (run_id);
