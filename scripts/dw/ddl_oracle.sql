CREATE TABLE dim_causa (
    id_causa        unknown NOT NULL,
    "cie-10_code"   unknown,
    "cie-10_nombre" unknown,
    gbd_code        unknown,
    gbd_nombre      unknown 
 

);

ALTER TABLE dim_causa ADD CONSTRAINT dim_causa_pk PRIMARY KEY ( id_causa );

CREATE TABLE dim_etario (
    id_etario         unknown NOT NULL,
    grupo_edad_codigo unknown,
    grupo_edad        unknown,
    categoria_etaria  unknown,
    edad_minima       unknown,
    edad_maxima       unknown 
 

);

ALTER TABLE dim_etario ADD CONSTRAINT dim_etario_pk PRIMARY KEY ( id_etario );

CREATE TABLE dim_genero (
    id_genero   unknown NOT NULL,
    sexo_codigo unknown,
    sexo_nombre unknown 
 

);

ALTER TABLE dim_genero ADD CONSTRAINT dim_genero_pk PRIMARY KEY ( id_genero );

CREATE TABLE dim_geografia (
    id_geografia    unknown NOT NULL,
    pais_iso3       unknown,
    pais_nombre     unknown,
    dep_ocurrencia  unknown,
    mun_ocurrencia  unknown,
    lugar_defuncion unknown 
 

);

ALTER TABLE dim_geografia ADD CONSTRAINT dim_geografia_pk PRIMARY KEY ( id_geografia );

CREATE TABLE dim_ihme_perfil (
    id_ihme_perfil unknown NOT NULL,
    metrica        unknown,
    medida         unknown 
 

);

ALTER TABLE dim_ihme_perfil ADD CONSTRAINT dim_ihme_perfil_pk PRIMARY KEY ( id_ihme_perfil );

CREATE TABLE dim_ine_perfil (
    id_ine_perfil     unknown NOT NULL,
    estado_civil      unknown,
    escolaridad       unknown,
    asistencia_medica unknown,
    tipo_ocurrencia   unknown 
 

);

ALTER TABLE dim_ine_perfil ADD CONSTRAINT dim_ine_perfil_pk PRIMARY KEY ( id_ine_perfil );

CREATE TABLE dim_source (
    id_source    unknown NOT NULL,
    source       unknown,
    ingestion_ts unknown,
    record_hash  unknown 
 

);

ALTER TABLE dim_source ADD CONSTRAINT dim_source_pk PRIMARY KEY ( id_source );

CREATE TABLE dim_tiempo (
    id_tiempo             unknown NOT NULL,
    mes_ocurrencia        unknown,
    mes_ocurrencia_num    unknown,
    anio_ocurrencia       unknown,
    semana_epidemiologica unknown,
    es_pre_covid          unknown 
 

);

ALTER TABLE dim_tiempo ADD CONSTRAINT dim_tiempo_pk PRIMARY KEY ( id_tiempo );

CREATE TABLE fact_ihme (
    valor           unknown,
    limite_inferior unknown,
    limite_superior unknown,
    id_geografia    unknown NOT NULL,
    id_genero       unknown NOT NULL,
    id_causa        unknown NOT NULL,
    id_tiempo       unknown NOT NULL,
    id_source       unknown NOT NULL,
    id_ihme_perfil  unknown NOT NULL
);

ALTER TABLE fact_ihme
    ADD CONSTRAINT fact_ihme_pk
        PRIMARY KEY ( id_geografia,
                      id_genero,
                      id_causa,
                      id_tiempo,
                      id_source,
                      id_ihme_perfil );

CREATE TABLE fact_ine (
    defuncion     unknown,
    id_geografia  unknown NOT NULL,
    id_tiempo     unknown NOT NULL,
    id_source     unknown NOT NULL,
    id_causa      unknown NOT NULL,
    id_etario     unknown NOT NULL,
    id_genero     unknown NOT NULL,
    id_ine_perfil unknown NOT NULL
);

ALTER TABLE fact_ine
    ADD CONSTRAINT fact_ine_pk
        PRIMARY KEY ( id_geografia,
                      id_tiempo,
                      id_source,
                      id_causa,
                      id_etario,
                      id_genero,
                      id_ine_perfil );

CREATE TABLE fact_mspas (
    defunciones   unknown,
    tasa_por_100k unknown,
    id_geografia  unknown NOT NULL,
    id_source     unknown NOT NULL,
    id_tiempo     unknown NOT NULL
);

ALTER TABLE fact_mspas
    ADD CONSTRAINT fact_mspas_pk PRIMARY KEY ( id_geografia,
                                               id_source,
                                               id_tiempo );

CREATE TABLE fact_panama (
    id_etario    unknown NOT NULL,
    id_causa     unknown NOT NULL,
    id_genero    unknown NOT NULL,
    id_source    unknown NOT NULL,
    id_tiempo    unknown NOT NULL,
    id_geografia unknown NOT NULL,
    defunciones  unknown 
 

);

ALTER TABLE fact_panama
    ADD CONSTRAINT fact_panama_pk
        PRIMARY KEY ( id_etario,
                      id_causa,
                      id_genero,
                      id_source,
                      id_tiempo,
                      id_geografia );

CREATE TABLE fact_who_deaths (
    "number"                                      unknown,
    prc_cause_specific_deaths_out_of_total_deaths unknown,
    age_std_death_rate_per_100k_std_population    unknown,
    death_rate_per_100k_population                unknown,
    id_source                                     unknown NOT NULL,
    id_geografia                                  unknown NOT NULL,
    id_causa                                      unknown NOT NULL,
    id_tiempo                                     unknown NOT NULL,
    id_genero                                     unknown NOT NULL
);

ALTER TABLE fact_who_deaths
    ADD CONSTRAINT who_deaths_pk
        PRIMARY KEY ( id_source,
                      id_geografia,
                      id_causa,
                      id_tiempo,
                      id_genero );

CREATE TABLE fact_who_population (
    population   unknown,
    id_source    unknown NOT NULL,
    id_tiempo    unknown NOT NULL,
    id_geografia unknown NOT NULL,
    id_genero    unknown NOT NULL,
    id_etario    unknown NOT NULL
);

ALTER TABLE fact_who_population
    ADD CONSTRAINT fact_who_population_pk
        PRIMARY KEY ( id_source,
                      id_tiempo,
                      id_geografia,
                      id_genero,
                      id_etario );

ALTER TABLE fact_ihme
    ADD CONSTRAINT fact_ihme_dim_causa_fk FOREIGN KEY ( id_causa )
        REFERENCES dim_causa ( id_causa );

ALTER TABLE fact_ihme
    ADD CONSTRAINT fact_ihme_dim_genero_fk FOREIGN KEY ( id_genero )
        REFERENCES dim_genero ( id_genero );

ALTER TABLE fact_ihme
    ADD CONSTRAINT fact_ihme_dim_geografia_fk FOREIGN KEY ( id_geografia )
        REFERENCES dim_geografia ( id_geografia );

ALTER TABLE fact_ihme
    ADD CONSTRAINT fact_ihme_dim_ihme_perfil_fk FOREIGN KEY ( id_ihme_perfil )
        REFERENCES dim_ihme_perfil ( id_ihme_perfil );

ALTER TABLE fact_ihme
    ADD CONSTRAINT fact_ihme_dim_source_fk FOREIGN KEY ( id_source )
        REFERENCES dim_source ( id_source );

ALTER TABLE fact_ihme
    ADD CONSTRAINT fact_ihme_dim_tiempo_fk FOREIGN KEY ( id_tiempo )
        REFERENCES dim_tiempo ( id_tiempo );

ALTER TABLE fact_ine
    ADD CONSTRAINT fact_ine_dim_causa_fk FOREIGN KEY ( id_causa )
        REFERENCES dim_causa ( id_causa );

ALTER TABLE fact_ine
    ADD CONSTRAINT fact_ine_dim_etario_fk FOREIGN KEY ( id_etario )
        REFERENCES dim_etario ( id_etario );

ALTER TABLE fact_ine
    ADD CONSTRAINT fact_ine_dim_genero_fk FOREIGN KEY ( id_genero )
        REFERENCES dim_genero ( id_genero );

ALTER TABLE fact_ine
    ADD CONSTRAINT fact_ine_dim_geografia_fk FOREIGN KEY ( id_geografia )
        REFERENCES dim_geografia ( id_geografia );

ALTER TABLE fact_ine
    ADD CONSTRAINT fact_ine_dim_ine_perfil_fk FOREIGN KEY ( id_ine_perfil )
        REFERENCES dim_ine_perfil ( id_ine_perfil );

ALTER TABLE fact_ine
    ADD CONSTRAINT fact_ine_dim_source_fk FOREIGN KEY ( id_source )
        REFERENCES dim_source ( id_source );

ALTER TABLE fact_ine
    ADD CONSTRAINT fact_ine_dim_tiempo_fk FOREIGN KEY ( id_tiempo )
        REFERENCES dim_tiempo ( id_tiempo );

ALTER TABLE fact_mspas
    ADD CONSTRAINT fact_mspas_dim_geografia_fk FOREIGN KEY ( id_geografia )
        REFERENCES dim_geografia ( id_geografia );

ALTER TABLE fact_mspas
    ADD CONSTRAINT fact_mspas_dim_source_fk FOREIGN KEY ( id_source )
        REFERENCES dim_source ( id_source );

ALTER TABLE fact_mspas
    ADD CONSTRAINT fact_mspas_dim_tiempo_fk FOREIGN KEY ( id_tiempo )
        REFERENCES dim_tiempo ( id_tiempo );

ALTER TABLE fact_panama
    ADD CONSTRAINT fact_panama_dim_causa_fk FOREIGN KEY ( id_causa )
        REFERENCES dim_causa ( id_causa );

ALTER TABLE fact_panama
    ADD CONSTRAINT fact_panama_dim_etario_fk FOREIGN KEY ( id_etario )
        REFERENCES dim_etario ( id_etario );

ALTER TABLE fact_panama
    ADD CONSTRAINT fact_panama_dim_genero_fk FOREIGN KEY ( id_genero )
        REFERENCES dim_genero ( id_genero );

ALTER TABLE fact_panama
    ADD CONSTRAINT fact_panama_dim_geografia_fk FOREIGN KEY ( id_geografia )
        REFERENCES dim_geografia ( id_geografia );

ALTER TABLE fact_panama
    ADD CONSTRAINT fact_panama_dim_source_fk FOREIGN KEY ( id_source )
        REFERENCES dim_source ( id_source );

ALTER TABLE fact_panama
    ADD CONSTRAINT fact_panama_dim_tiempo_fk FOREIGN KEY ( id_tiempo )
        REFERENCES dim_tiempo ( id_tiempo );

ALTER TABLE fact_who_population
    ADD CONSTRAINT fact_who_population_dim_etario_fk FOREIGN KEY ( id_etario )
        REFERENCES dim_etario ( id_etario );

ALTER TABLE fact_who_population
    ADD CONSTRAINT fact_who_population_dim_genero_fk FOREIGN KEY ( id_genero )
        REFERENCES dim_genero ( id_genero );

ALTER TABLE fact_who_population
    ADD CONSTRAINT fact_who_population_dim_geografia_fk FOREIGN KEY ( id_geografia )
        REFERENCES dim_geografia ( id_geografia );

ALTER TABLE fact_who_population
    ADD CONSTRAINT fact_who_population_dim_source_fk FOREIGN KEY ( id_source )
        REFERENCES dim_source ( id_source );

ALTER TABLE fact_who_population
    ADD CONSTRAINT fact_who_population_dim_tiempo_fk FOREIGN KEY ( id_tiempo )
        REFERENCES dim_tiempo ( id_tiempo );

ALTER TABLE fact_who_deaths
    ADD CONSTRAINT who_deaths_dim_causa_fk FOREIGN KEY ( id_causa )
        REFERENCES dim_causa ( id_causa );

ALTER TABLE fact_who_deaths
    ADD CONSTRAINT who_deaths_dim_genero_fk FOREIGN KEY ( id_genero )
        REFERENCES dim_genero ( id_genero );

ALTER TABLE fact_who_deaths
    ADD CONSTRAINT who_deaths_dim_geografia_fk FOREIGN KEY ( id_geografia )
        REFERENCES dim_geografia ( id_geografia );

ALTER TABLE fact_who_deaths
    ADD CONSTRAINT who_deaths_dim_source_fk FOREIGN KEY ( id_source )
        REFERENCES dim_source ( id_source );

ALTER TABLE fact_who_deaths
    ADD CONSTRAINT who_deaths_dim_tiempo_fk FOREIGN KEY ( id_tiempo )
        REFERENCES dim_tiempo ( id_tiempo );



