"""Chart parameter definitions for all 14 Superset charts across 3 dashboards.

Every function returns a dict suitable for passing to ``create_chart()``.
The configuration is separated from the framework so parameters can be
reviewed, version-controlled, and tested independently of the API layer.
"""

import os
import json


# ---------------------------------------------------------------------------
# Environment-driven configuration
# ---------------------------------------------------------------------------

SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://localhost:8088")
SUPERSET_USER = os.environ.get("SUPERSET_USER", "admin")
SUPERSET_PASS = os.environ.get("SUPERSET_PASS", "admin")

GREENPLUM_HOST = os.environ.get("GREENPLUM_HOST", "dw-greenplum")
GREENPLUM_PORT = os.environ.get("GREENPLUM_PORT", "5432")
GREENPLUM_DB = os.environ.get("GREENPLUM_DB", "dw_semis2")
GREENPLUM_USER = os.environ.get("GREENPLUM_USER", "gpadmin")
GREENPLUM_PASS = os.environ.get("PGPASSWORD", os.environ.get("GREENPLUM_PASS", "semis2_grupo11"))


def greenplum_uri() -> str:
    """Build the SQLAlchemy URI for Greenplum."""
    return (
        f"postgresql://{GREENPLUM_USER}:{GREENPLUM_PASS}"
        f"@{GREENPLUM_HOST}:{GREENPLUM_PORT}/{GREENPLUM_DB}"
    )


# ---------------------------------------------------------------------------
# Database & dataset definitions
# ---------------------------------------------------------------------------

DB_NAME = "Greenplum DW"
DB_URI = greenplum_uri()

DATASETS = [
    {"name": "INE - Mortalidad Completa",    "schema": "dm_mortality", "table": "v_ine_completa"},
    {"name": "MSPAS - Mortalidad Nacional",  "schema": "dm_mortality", "table": "v_mspas_nacional"},
    {"name": "IHME - Carga Enfermedad CA",   "schema": "dm_mortality", "table": "v_ihme_centroamerica"},
    {"name": "WHO - Población Guatemala",     "schema": "dm_mortality", "table": "v_poblacion_guatemala"},
]

DASHBOARDS = [
    "Pre vs Post COVID — Guatemala",
    "Causas de Muerte",
    "Geografia y Demografia",
]


# ---------------------------------------------------------------------------
# GeoJSON loader (for deck.gl polygon map)
# ---------------------------------------------------------------------------

def _load_geojson() -> dict:
    """Load Guatemala departamentos GeoJSON from the geodata directory."""
    geojson_path = os.path.join(
        os.path.dirname(__file__), "..", "geodata", "guatemala_departamentos.geojson",
    )
    with open(geojson_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Individual chart config factories
# ---------------------------------------------------------------------------

def _chart(slice_name: str, viz_type: str, datasource_id: int,
           params: dict, datasource_type: str = "table",
           legacy_slice_names: list[str] | None = None) -> dict:
    """Construct a standard chart configuration dict."""
    config = {
        "slice_name": slice_name,
        "viz_type": viz_type,
        "datasource_id": datasource_id,
        "datasource_type": datasource_type,
        "params": params,
    }
    if legacy_slice_names:
        config["legacy_slice_names"] = legacy_slice_names
    return config


def _metric(column: str, aggregate: str = "SUM", label: str | None = None) -> dict:
    """Return a Superset SIMPLE metric with a stable, unique label."""
    return {
        "expressionType": "SIMPLE",
        "column": {"column_name": column},
        "aggregate": aggregate,
        "label": label or f"{aggregate}({column})",
    }


def _sql_metric(sql: str, label: str) -> dict:
    """Return a Superset SQL metric with a stable label."""
    return {"expressionType": "SQL", "sqlExpression": sql, "label": label}


CHART_COLORS = ["#38bdf8", "#22c55e", "#f59e0b", "#ef4444", "#a78bfa", "#14b8a6"]


def _visual_defaults() -> dict:
    """Shared visual defaults for polished dashboard charts."""
    return {
        "color_scheme": "supersetColors",
        "show_legend": True,
        "legendOrientation": "top",
        "rich_tooltip": True,
        "show_value": False,
        "row_limit": 10000,
    }


# ===================================================================
# DASHBOARD 1: Pre vs Post COVID — Guatemala (6 charts)
# ===================================================================

def chart_1_1_kpi_pre_covid(ine_dataset_id: int) -> dict:
    """KPI: Total Defunciones Pre-COVID (2015–2019)."""
    return _chart(
        "Total Defunciones Pre-COVID (2015-2019)",
        "big_number_total",
        ine_dataset_id,
        {
            "metric": _metric("defuncion", label="Defunciones pre-COVID"),
            "subheader": "2015–2019",
            "header_font_size": 0.35,
            "subheader_font_size": 0.15,
            "adhoc_filters": [
                {
                    "clause": "WHERE",
                    "expressionType": "SQL",
                    "sqlExpression": "anio_ocurrencia BETWEEN 2015 AND 2019",
                },
            ],
        },
    )


def chart_1_2_kpi_post_covid(ine_dataset_id: int) -> dict:
    """KPI: Total Defunciones Post-COVID (2020–2024)."""
    return _chart(
        "Total Defunciones Post-COVID (2020-2024)",
        "big_number_total",
        ine_dataset_id,
        {
            "metric": _metric("defuncion", label="Defunciones post-COVID"),
            "subheader": "2020–2024",
            "header_font_size": 0.35,
            "subheader_font_size": 0.15,
            "adhoc_filters": [
                {
                    "clause": "WHERE",
                    "expressionType": "SQL",
                    "sqlExpression": "anio_ocurrencia BETWEEN 2020 AND 2024",
                },
            ],
        },
    )


def chart_1_3_kpi_variacion(ine_dataset_id: int) -> dict:
    """KPI: Variacion porcentual Pre vs Post COVID.

    Custom SQL metric computing percentage change between the two periods.
    """
    var_sql = (
        "(SUM(CASE WHEN anio_ocurrencia BETWEEN 2020 AND 2024 THEN defuncion ELSE 0 END)"
        " - SUM(CASE WHEN anio_ocurrencia BETWEEN 2015 AND 2019 THEN defuncion ELSE 0 END))"
        " / NULLIF(SUM(CASE WHEN anio_ocurrencia BETWEEN 2015 AND 2019 THEN defuncion ELSE 0 END), 0) * 100"
    )
    return _chart(
        "Variacion Pre vs Post COVID",
        "big_number_total",
        ine_dataset_id,
        {
            "metric": _sql_metric(var_sql, "Variacion %"),
            "subheader": "Cambio relativo",
            "y_axis_format": ".1f",
            "header_font_size": 0.35,
            "subheader_font_size": 0.15,
        },
    )


def chart_1_4_serie_temporal_mensual(ine_dataset_id: int) -> dict:
    """Time-series area: Defunciones Mensuales 2015–2024."""
    return _chart(
        "Defunciones Mensuales 2015-2024",
        "echarts_timeseries_line",
        ine_dataset_id,
        {
            **_visual_defaults(),
            "metrics": [_metric("defuncion", label="Defunciones")],
            "groupby": ["pre_post_covid"],
            "x_axis": "fecha_mes",
            "time_grain_sqla": "P1M",
            "granularity_sqla": "fecha_mes",
            "contributionMode": None,
            "stack": True,
            "adhoc_filters": [
                {
                    "clause": "WHERE",
                    "expressionType": "SQL",
                    "sqlExpression": "anio_ocurrencia BETWEEN 2015 AND 2024",
                },
            ],
            "markerEnabled": False,
            "y_axis_format": "~s",
        },
    )


def chart_1_5_barras_anuales_pre_post(ine_dataset_id: int) -> dict:
    """Bar chart: Defunciones por Ano, colour-coded by pre/post COVID."""
    return _chart(
        "Defunciones por Ano — Pre vs Post COVID",
        "echarts_timeseries_bar",
        ine_dataset_id,
        {
            **_visual_defaults(),
            "metrics": [_metric("defuncion", label="Defunciones")],
            "groupby": ["pre_post_covid"],
            "x_axis": "fecha_anio",
            "time_grain_sqla": "P1Y",
            "granularity_sqla": "fecha_anio",
            "stack": False,
            "adhoc_filters": [
                {
                    "clause": "WHERE",
                    "expressionType": "SQL",
                    "sqlExpression": "anio_ocurrencia BETWEEN 2015 AND 2024",
                },
            ],
            "y_axis_format": "~s",
        },
    )


def chart_1_6_tasa_mspas(mspas_dataset_id: int) -> dict:
    """Line chart: Tasa de Mortalidad Nacional x 100k hab (MSPAS)."""
    return _chart(
        "Tasa de Mortalidad Nacional x 100k hab (MSPAS)",
        "echarts_timeseries_line",
        mspas_dataset_id,
        {
            **_visual_defaults(),
            "metrics": [_metric("tasa_por_100k", "AVG", "Tasa x100k")],
            "x_axis": "fecha_anio",
            "time_grain_sqla": "P1Y",
            "granularity_sqla": "fecha_anio",
            "markerEnabled": True,
            "y_axis_format": ".1f",
        },
    )


# ===================================================================
# DASHBOARD 2: Causas de Muerte (4 charts)
# ===================================================================

def chart_2_1_treemap_causas_gbd(ine_dataset_id: int) -> dict:
    """Treemap: Defunciones por Causa GBD Nivel 2."""
    return _chart(
        "Defunciones por Causa GBD L2",
        "treemap_v2",
        ine_dataset_id,
        {
            "metric": _metric("defuncion", label="Defunciones"),
            "groupby": ["gbd_nombre"],
            "row_limit": 20,
            "color_scheme": "supersetColors",
            "show_labels": True,
        },
    )


def chart_2_2_top10_causas(ine_dataset_id: int) -> dict:
    """Treemap: top causes with compact visual hierarchy."""
    return _chart(
        "Top 10 Causas de Muerte",
        "treemap_v2",
        ine_dataset_id,
        {
            "metric": _metric("defuncion", label="Defunciones"),
            "groupby": ["gbd_nombre"],
            "color_scheme": "supersetColors",
            "show_labels": True,
            "row_limit": 10,
        },
    )


def chart_2_3_pre_post_por_causa(ine_dataset_id: int) -> dict:
    """Line chart: annual deaths split by COVID period."""
    return _chart(
        "Tendencia Pre vs Post COVID",
        "echarts_timeseries_line",
        ine_dataset_id,
        {
            **_visual_defaults(),
            "metrics": [_metric("defuncion", label="Defunciones")],
            "groupby": ["pre_post_covid"],
            "x_axis": "fecha_anio",
            "time_grain_sqla": "P1Y",
            "granularity_sqla": "fecha_anio",
            "stack": False,
            "y_axis_format": "~s",
        },
        legacy_slice_names=["Top 5 Causas — Pre vs Post COVID"],
    )


def chart_2_4_evolucion_regional_ihme(ihme_dataset_id: int) -> dict:
    """Line chart: Tendencia de Causas en Centroamerica (IHME).

    Filters to the top 3 GBD causes and groups by year for IHME data
    where ``medida='Deaths'`` and ``metrica='Number'``.
    """
    return _chart(
        "Tendencia de Causas en Centroamerica (IHME)",
        "echarts_timeseries_line",
        ihme_dataset_id,
        {
            **_visual_defaults(),
            "metrics": [_metric("valor", label="Muertes")],
            "groupby": ["pais_nombre"],
            "x_axis": "fecha_anio",
            "time_grain_sqla": "P1Y",
            "granularity_sqla": "fecha_anio",
            "adhoc_filters": [],
            "y_axis_format": "~s",
        },
    )


# ===================================================================
# DASHBOARD 3: Geografia y Demografia (4 charts)
# ===================================================================

def chart_3_1_mapa_departamento(ine_dataset_id: int) -> dict:
    """Treemap: Defunciones por departamento.

    This keeps the geography story visual and avoids the local deck.gl issue
    where the map rendered the world without department polygons.
    """
    return _chart(
        "Defunciones por Departamento",
        "treemap_v2",
        ine_dataset_id,
        {
            "metric": _metric("defuncion", label="Defunciones"),
            "groupby": ["dep_ocurrencia"],
            "row_limit": 22,
            "color_scheme": "supersetColors",
            "show_labels": True,
        },
        legacy_slice_names=["Tasa de Mortalidad por Departamento"],
    )


def chart_3_2_heatmap_edad_anio(ine_dataset_id: int) -> dict:
    """Stacked bar: Defunciones por grupo etario y año."""
    return _chart(
        "Defunciones por Grupo Etario y Ano",
        "echarts_timeseries_bar",
        ine_dataset_id,
        {
            **_visual_defaults(),
            "metrics": [_metric("defuncion", label="Defunciones")],
            "groupby": ["categoria_etaria"],
            "x_axis": "fecha_anio",
            "time_grain_sqla": "P1Y",
            "granularity_sqla": "fecha_anio",
            "stack": True,
            "y_axis_format": "~s",
        },
    )


def chart_3_3_distribucion_sexo_edad(ine_dataset_id: int) -> dict:
    """Stacked bar: annual deaths split by sex."""
    return _chart(
        "Defunciones por Sexo y Año",
        "echarts_timeseries_bar",
        ine_dataset_id,
        {
            **_visual_defaults(),
            "metrics": [_metric("defuncion", label="Defunciones")],
            "groupby": ["sexo_nombre"],
            "x_axis": "fecha_anio",
            "time_grain_sqla": "P1Y",
            "granularity_sqla": "fecha_anio",
            "stack": True,
            "y_axis_format": "~s",
        },
        legacy_slice_names=["Defunciones por Sexo y Grupo Etario"],
    )


def chart_3_4_pivot_resumen(ine_dataset_id: int) -> dict:
    """Pivot table: Resumen Departamento x Causa."""
    return _chart(
        "Resumen: Departamento x Causa",
        "pivot_table_v2",
        ine_dataset_id,
        {
            "columns": ["dep_ocurrencia"],
            "rows": ["gbd_nombre"],
            "metrics": [_metric("defuncion", label="Defunciones")],
            "row_limit": 10000,
        },
    )


# ---------------------------------------------------------------------------
# Dashboard → chart mapping (used by the orchestrator)
# ---------------------------------------------------------------------------

def dashboard1_charts(ine_id: int, mspas_id: int) -> list[dict]:
    """Return chart config list for Dashboard 1 'Pre vs Post COVID'."""
    return [
        chart_1_1_kpi_pre_covid(ine_id),
        chart_1_2_kpi_post_covid(ine_id),
        chart_1_3_kpi_variacion(ine_id),
        chart_1_4_serie_temporal_mensual(ine_id),
        chart_1_5_barras_anuales_pre_post(ine_id),
        chart_1_6_tasa_mspas(mspas_id),
    ]


def dashboard2_charts(ine_id: int, ihme_id: int) -> list[dict]:
    """Return chart config list for Dashboard 2 'Causas de Muerte'."""
    return [
        chart_2_1_treemap_causas_gbd(ine_id),
        chart_2_2_top10_causas(ine_id),
        chart_2_3_pre_post_por_causa(ine_id),
        chart_2_4_evolucion_regional_ihme(ihme_id),
    ]


def dashboard3_charts(ine_id: int) -> list[dict]:
    """Return chart config list for Dashboard 3 'Geografia y Demografia'."""
    return [
        chart_3_1_mapa_departamento(ine_id),
        chart_3_2_heatmap_edad_anio(ine_id),
        chart_3_3_distribucion_sexo_edad(ine_id),
        chart_3_4_pivot_resumen(ine_id),
    ]
