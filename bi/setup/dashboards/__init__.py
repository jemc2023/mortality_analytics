"""Dashboard chart configuration modules for Mortality Analytics.

Each module defines the chart configurations and layout for one
analytical dashboard, re-exporting chart factories from
``bi.setup.config`` for use by the orchestrator.
"""

from bi.setup.dashboards.dash1_pre_post_covid import DASH1_TITLE, dash1_charts
from bi.setup.dashboards.dash2_causas_muerte import DASH2_TITLE, dash2_charts
from bi.setup.dashboards.dash3_geografia_demografia import DASH3_TITLE, dash3_charts

__all__ = [
    "DASH1_TITLE",
    "dash1_charts",
    "DASH2_TITLE",
    "dash2_charts",
    "DASH3_TITLE",
    "dash3_charts",
]
