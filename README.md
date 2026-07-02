# Plataforma Analítica de Mortalidad End-to-End

**Seminario de Sistemas 2 — Laboratorio de Ingeniería de Datos | USAC 2026**  
Análisis de mortalidad Pre-COVID (2015–2019) vs Post-COVID (2020+) en Guatemala y Centroamérica.

## Estructura

```
├── docs/          ← enunciado y documentación del proyecto
├── scripts/
│   ├── ingestion/     ← Google Drive, SharePoint, S3, RDS connectors
│   ├── cleaning/      ← normalization, ICD-10, deduplication
│   └── transformation/ ← Sandbox → Stage → Fact
├── sql/           ← DDL de tablas (sandbox, stage, fact, dimensiones)
├── glue-jobs/     ← jobs de AWS Glue (ETL)
├── notebooks/     ← exploración y EDA
├── ml/            ← modelos SageMaker / Databricks
├── bi/            ← dashboards Power BI y Metabase
└── data/          ← no versionado (ver .gitignore)
```

## Fases

| Fase | Descripción | Ponderación |
|------|-------------|-------------|
| Fase 1 | Identificación, limpieza e ingesta → Sandbox | 30% |
| Fase 2 | Transformación por capas → Data Warehouse (nube + local) | 35% |
| Fase 3 | Machine Learning + visualización BI | 30% |
| Tarea | Integraciones Databricks | 5% |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> Las credenciales (`credentials.json`, `token.json`, `.env`) no están versionadas.
