"""Dashboard 1 — 'Pre vs Post COVID — Guatemala'.

Chart configuration and layout for the comparative mortality trends
dashboard. Six visualizations spanning KPIs, time-series, and official
MSPAS rate validation.

Data sources:
    - v_ine_completa   (5 charts)
    - v_mspas_nacional (1 chart)

Dashboard layout:
    Row 1: KPI Pre-COVID | KPI Post-COVID | Variacion %
    Row 2: Serie temporal mensual (full width)
    Row 3: Barras anuales pre/post | Tasa MSPAS
"""

from bi.setup.config import (
    chart_1_1_kpi_pre_covid,
    chart_1_2_kpi_post_covid,
    chart_1_3_kpi_variacion,
    chart_1_4_serie_temporal_mensual,
    chart_1_5_barras_anuales_pre_post,
    chart_1_6_tasa_mspas,
)

DASH1_TITLE = "Pre vs Post COVID — Guatemala"


def dash1_charts(ine_dataset_id: int, mspas_dataset_id: int) -> list[dict]:
    """Return the ordered list of chart configs for Dashboard 1.

    Args:
        ine_dataset_id:   Dataset ID for v_ine_completa.
        mspas_dataset_id: Dataset ID for v_mspas_nacional.

    Returns:
        List of chart configuration dicts, in display order.
    """
    return [
        chart_1_1_kpi_pre_covid(ine_dataset_id),
        chart_1_2_kpi_post_covid(ine_dataset_id),
        chart_1_3_kpi_variacion(ine_dataset_id),
        chart_1_4_serie_temporal_mensual(ine_dataset_id),
        chart_1_5_barras_anuales_pre_post(ine_dataset_id),
        chart_1_6_tasa_mspas(mspas_dataset_id),
    ]
