"""Dashboard 2 — 'Causas de Muerte'.

Chart configuration and layout for the cause-of-death deep-dive
dashboard. Four visualizations spanning treemap, ranked bars,
pre/post comparison, and regional IHME context.

Data sources:
    - v_ine_completa        (3 charts)
    - v_ihme_centroamerica   (1 chart)

Dashboard layout:
    Row 1: Treemap causas GBD (full width)
    Row 2: Top 10 causas | Pre vs Post por causa
    Row 3: Evolución regional IHME (full width)
"""

from bi.setup.config import (
    chart_2_1_treemap_causas_gbd,
    chart_2_2_top10_causas,
    chart_2_3_pre_post_por_causa,
    chart_2_4_evolucion_regional_ihme,
)

DASH2_TITLE = "Causas de Muerte"


def dash2_charts(ine_dataset_id: int, ihme_dataset_id: int) -> list[dict]:
    """Return the ordered list of chart configs for Dashboard 2.

    Args:
        ine_dataset_id:  Dataset ID for v_ine_completa.
        ihme_dataset_id: Dataset ID for v_ihme_centroamerica.

    Returns:
        List of chart configuration dicts, in display order.
    """
    return [
        chart_2_1_treemap_causas_gbd(ine_dataset_id),
        chart_2_2_top10_causas(ine_dataset_id),
        chart_2_3_pre_post_por_causa(ine_dataset_id),
        chart_2_4_evolucion_regional_ihme(ihme_dataset_id),
    ]
