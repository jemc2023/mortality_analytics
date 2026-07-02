"""Dashboard 3 — 'Geografía y Demografía'.

Chart configuration and layout for the geographic and demographic
analysis dashboard. Four visualizations spanning deck.gl polygon map,
heatmap, age/sex distribution, and a pivot table summary.

Data source:
    - v_ine_completa (4 charts)

Dashboard layout:
    Row 1: Mapa coroplético por departamento (full width)
    Row 2: Heatmap edad x año | Distribución sexo y edad
    Row 3: Pivot table resumen (full width)
"""

from bi.setup.config import (
    chart_3_1_mapa_departamento,
    chart_3_2_heatmap_edad_anio,
    chart_3_3_distribucion_sexo_edad,
    chart_3_4_pivot_resumen,
)

DASH3_TITLE = "Geografia y Demografia"


def dash3_charts(ine_dataset_id: int) -> list[dict]:
    """Return the ordered list of chart configs for Dashboard 3.

    Args:
        ine_dataset_id: Dataset ID for v_ine_completa.

    Returns:
        List of chart configuration dicts, in display order.
    """
    return [
        chart_3_1_mapa_departamento(ine_dataset_id),
        chart_3_2_heatmap_edad_anio(ine_dataset_id),
        chart_3_3_distribucion_sexo_edad(ine_dataset_id),
        chart_3_4_pivot_resumen(ine_dataset_id),
    ]
