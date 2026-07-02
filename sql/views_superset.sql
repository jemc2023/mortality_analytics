--
-- views_superset.sql — Vistas pre-join para Apache Superset
-- ============================================================================
-- Propósito: Desnormalizar las tablas de hechos con sus dimensiones en el
-- esquema dm_mortality, produciendo vistas planas que Superset puede consumir
-- directamente sin necesidad de definir joins complejos en el explorador.
--
-- Convenciones:
--   - Cada vista documenta su fuente, grano y filtros aplicados.
--   - Se usan nombres de columna en snake_case español tal como vienen de la DDL.
--   - Las llaves foráneas (id_*) son BIGINT NOT NULL → INNER JOIN es seguro.
--   - CREATE OR REPLACE VIEW permite ejecución idempotente con psql -f.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. v_ine_completa — Mortalidad INE (Guatemala) completamente desnormalizada
-- ---------------------------------------------------------------------------
-- Fuente:  fact_ine + dim_tiempo + dim_geografia + dim_causa + dim_etario
--          + dim_genero + dim_ine_perfil
-- Grano:   Un registro por defunción individual INE
--          (id_geografia + id_tiempo + id_causa + id_etario + id_genero
--           + id_ine_perfil)
-- Filtros: Sin filtro de año; cubre 2015–2024 completo (pre y post-COVID).
--          La columna pre_post_covid se deriva de dim_tiempo.es_pre_covid para
--          segmentar fácilmente en dashboards de comparación temporal.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW dm_mortality.v_ine_completa AS
SELECT
    f.id_geografia,
    f.id_tiempo,
    f.id_causa,
    f.id_etario,
    f.id_genero,
    f.id_ine_perfil,
    f.defuncion,
    -- dim_geografia
    g.pais_iso3,
    g.pais_nombre,
    g.dep_ocurrencia,
    g.mun_ocurrencia,
    -- dim_tiempo
    t.anio_ocurrencia,
    t.mes_ocurrencia,
    t.mes_ocurrencia_num,
    t.es_pre_covid,
    CASE WHEN t.es_pre_covid THEN 'Pre-COVID' ELSE 'COVID/Post' END AS pre_post_covid,
    -- dim_causa
    c.cie10_code,
    c.cie10_nombre,
    c.gbd_code,
    c.gbd_nombre,
    -- dim_etario
    e.grupo_edad,
    e.categoria_etaria,
    -- dim_genero
    ge.sexo_nombre,
    -- dim_ine_perfil
    p.estado_civil,
    p.escolaridad,
    p.asistencia_medica,
    -- columnas temporales agregadas al final para compatibilidad con CREATE OR REPLACE VIEW
    TO_DATE(t.anio_ocurrencia::text || '-01-01', 'YYYY-MM-DD') AS fecha_anio,
    TO_DATE(
        t.anio_ocurrencia::text || '-' || LPAD(t.mes_ocurrencia_num::text, 2, '0') || '-01',
        'YYYY-MM-DD'
    ) AS fecha_mes
FROM dm_mortality.fact_ine        f
JOIN dm_mortality.dim_tiempo      t ON f.id_tiempo      = t.id_tiempo
JOIN dm_mortality.dim_geografia   g ON f.id_geografia   = g.id_geografia
JOIN dm_mortality.dim_causa       c ON f.id_causa       = c.id_causa
JOIN dm_mortality.dim_etario      e ON f.id_etario      = e.id_etario
JOIN dm_mortality.dim_genero      ge ON f.id_genero      = ge.id_genero
JOIN dm_mortality.dim_ine_perfil  p ON f.id_ine_perfil  = p.id_ine_perfil;

-- ---------------------------------------------------------------------------
-- 2. v_mspas_nacional — Mortalidad general MSPAS (Guatemala, nivel nacional)
-- ---------------------------------------------------------------------------
-- Fuente:  fact_mspas + dim_tiempo + dim_geografia
-- Grano:   Un registro por año (mortalidad general reportada por MSPAS)
-- Filtros: Solo Guatemala (pais_iso3 = 'GTM').
--          La tasa_por_100k solo está poblada para años pre-COVID (≤2019);
--          para 2020–2022 aparece NULL. Ver modelo_dimensional.md §2.3.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW dm_mortality.v_mspas_nacional AS
SELECT
    t.anio_ocurrencia,
    t.es_pre_covid,
    g.pais_iso3,
    g.pais_nombre,
    f.defunciones,
    f.tasa_por_100k,
    TO_DATE(t.anio_ocurrencia::text || '-01-01', 'YYYY-MM-DD') AS fecha_anio
FROM dm_mortality.fact_mspas       f
JOIN dm_mortality.dim_tiempo       t ON f.id_tiempo     = t.id_tiempo
JOIN dm_mortality.dim_geografia    g ON f.id_geografia  = g.id_geografia
WHERE g.pais_iso3 = 'GTM';

-- ---------------------------------------------------------------------------
-- 3. v_ihme_centroamerica — Carga de enfermedad IHME para Centroamérica
-- ---------------------------------------------------------------------------
-- Fuente:  fact_ihme + dim_tiempo + dim_geografia + dim_causa + dim_genero
--          + dim_ihme_perfil
-- Grano:   Un registro por país × año × causa GBD × sexo × métrica × medida
-- Filtros: Solo métrica = 'Número' y medida = 'Deaths' (valores aditivos;
--          tasas y porcentajes NO son sumables — ver modelo_dimensional.md §2.4).
--          Solo países de Centroamérica (GTM, SLV, HND, NIC, CRI, PAN, BLZ).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW dm_mortality.v_ihme_centroamerica AS
SELECT
    t.anio_ocurrencia,
    t.es_pre_covid,
    g.pais_iso3,
    g.pais_nombre,
    c.gbd_nombre,
    ge.sexo_nombre,
    p.metrica,
    p.medida,
    f.valor,
    f.limite_inferior,
    f.limite_superior,
    TO_DATE(t.anio_ocurrencia::text || '-01-01', 'YYYY-MM-DD') AS fecha_anio
FROM dm_mortality.fact_ihme         f
JOIN dm_mortality.dim_tiempo        t ON f.id_tiempo       = t.id_tiempo
JOIN dm_mortality.dim_geografia     g ON f.id_geografia    = g.id_geografia
JOIN dm_mortality.dim_causa         c ON f.id_causa        = c.id_causa
JOIN dm_mortality.dim_genero        ge ON f.id_genero       = ge.id_genero
JOIN dm_mortality.dim_ihme_perfil   p ON f.id_ihme_perfil  = p.id_ihme_perfil
WHERE p.metrica = 'Número'
  AND p.medida = 'Deaths'
  AND g.pais_iso3 IN ('GTM', 'SLV', 'HND', 'NIC', 'CRI', 'PAN', 'BLZ');

-- ---------------------------------------------------------------------------
-- 4. v_poblacion_guatemala — Población WHO por grupo etario (Guatemala)
-- ---------------------------------------------------------------------------
-- Fuente:  fact_who_population + dim_tiempo + dim_geografia + dim_genero
--          + dim_etario
-- Grano:   Un registro por año × sexo × banda etaria quinquenal
-- Filtros: Solo Guatemala (pais_iso3 = 'GTM').
--          Útil como denominador para calcular tasas de mortalidad por
--          100 000 habitantes desde Superset.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW dm_mortality.v_poblacion_guatemala AS
SELECT
    t.anio_ocurrencia,
    g.pais_iso3,
    ge.sexo_nombre,
    e.grupo_edad,
    e.categoria_etaria,
    f.population,
    TO_DATE(t.anio_ocurrencia::text || '-01-01', 'YYYY-MM-DD') AS fecha_anio
FROM dm_mortality.fact_who_population  f
JOIN dm_mortality.dim_tiempo           t ON f.id_tiempo     = t.id_tiempo
JOIN dm_mortality.dim_geografia        g ON f.id_geografia  = g.id_geografia
JOIN dm_mortality.dim_genero           ge ON f.id_genero     = ge.id_genero
JOIN dm_mortality.dim_etario           e ON f.id_etario     = e.id_etario
WHERE g.pais_iso3 = 'GTM';
