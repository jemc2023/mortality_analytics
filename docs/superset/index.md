# Apache Superset — Visualización Analítica

## Rol en la Plataforma

Apache Superset es la **segunda herramienta de BI** de la plataforma Mortality Analytics (junto con Power BI). Cumple el requisito de la Fase 3 de demostrar interoperabilidad entre al menos dos herramientas de BI distintas, consumiendo los mismos datos del Data Warehouse.

## Arquitectura de Conexión

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Network: mortality-net          │
│                                                          │
│  ┌──────────────────┐         ┌──────────────────────┐   │
│  │   Greenplum DW   │         │   Apache Superset    │   │
│  │   dw-greenplum   │◄────────│   bi-superset        │   │
│  │   :5432          │  SQL    │   :8088              │   │
│  │   dw_semis2      │         │   (SQLite metadata)  │   │
│  └──────────────────┘         └──────────────────────┘   │
│         ▲                                                 │
│         │ replicación                                     │
│  ┌──────┴───────────┐                                    │
│  │  Databricks (nube)│                                    │
│  │  Delta Lake       │                                    │
│  └──────────────────┘                                    │
└──────────────────────────────────────────────────────────┘
```

**Principio de diseño**: Superset se conecta directamente al Greenplum local, que a su vez es réplica del Data Warehouse en Databricks (nube). Esto demuestra interoperabilidad **nube → local → BI**, donde el mismo dato viaja desde Delta Lake hasta dos herramientas de visualización distintas.

## Stack Tecnológico

| Componente | Tecnología | Justificación |
|------------|-----------|---------------|
| **Contenedor** | Docker (`apache/superset:latest`) | Despliegue reproducible, portable |
| **Metadata DB** | SQLite (interno) | Suficiente para demo académica, sin contenedores extra |
| **Conexión DW** | SQLAlchemy `postgresql://` | Greenplum es PostgreSQL-compatible |
| **Consultas** | Vistas SQL pre-join en `dm_mortality` | Esquema estrella desnormalizado para consumo directo |
| **Automatización** | Python + Superset REST API | Creación programática de dashboards, reproducible |
| **Geografía** | Treemap por departamento | Visual estable sin depender de Mapbox/tiles externos |

## Instalación y Uso

### Requisitos previos

- Docker y Docker Compose instalados
- Greenplum corriendo en `mortality-net` (`make up` desde `scripts/dw/`)
- Red Docker `mortality-net` creada: `docker network create mortality-net`
- Datos en Greenplum (ver sección de restauración abajo)

### Guía completa de reproducción (desde cero)

```bash
# ==== 1. Red Docker ====
docker network create mortality-net

# ==== 2. Levantar Greenplum ====
cd scripts/dw
make up
# Esperar ~40s a que Greenplum esté listo

# ==== 3. Restaurar datos desde backup ====
cd /ruta/proyecto
gunzip -c scripts/dw/backups/greenplum/dw_semis2_20260622_224200.dump.gz | \
  docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/pg_restore -h localhost -U gpadmin -d dw_semis2 \
  --clean --if-exists --no-owner --no-privileges

# ==== 4. Cargar vistas para Superset ====
docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/psql -h localhost -U gpadmin -d dw_semis2 \
  < sql/views_superset.sql

# ==== 5. Conectar Greenplum a la red ====
docker network connect mortality-net dw-greenplum

# ==== 6. Levantar Superset ====
cd bi
make up       # Construye imagen con psycopg2 + levanta contenedor
make init     # Crea admin, migraciones, permisos

# ==== 6b. Instalar driver PostgreSQL en el venv de Superset ====
# (El Dockerfile lo hace en el build, pero si falla, ejecutar manualmente:)
docker exec -u root bi-superset bash -c "
  pip install psycopg2-binary && 
  cp -r /usr/local/lib/python3.10/site-packages/psycopg2* /app/.venv/lib/python3.10/site-packages/
"

# ==== 6c. Crear conexión a Greenplum (vía CLI porque la API falla el test) ====
docker exec bi-superset superset set-database-uri \
  -d "Greenplum DW" \
  -u "postgresql://gpadmin:semis2_grupo11@dw-greenplum:5432/dw_semis2"

# ==== 6d. Crear datasets + charts + dashboards vía API ====
make setup

# ==== 6e. Métricas, formatos y layouts ====
# Usar el script post_setup.py (incluido en bi/setup/) que:
#   - Convierte métricas string a formato SIMPLE con labels explícitos
#   - Agrega time_range a todos los charts
#   - Arregla el position_json multi-columna de los 3 dashboards
#   - Guarda métricas SUM/AVG en los datasets
make post-setup

# ==== 7. Acceder ====
# http://localhost:8088 → admin/admin
# Dashboards: IDs 1 (Pre vs Post), 2 (Causas), 3 (Geografía)

# ==== 8. Detener ====
make down
```

### Acceso

- **URL**: [http://localhost:8088](http://localhost:8088)
- **Usuario**: `admin`
- **Contraseña**: `admin`
- **Conexión DW**: Greenplum DW (`postgresql://gpadmin:***@dw-greenplum:5432/dw_semis2`)

## Troubleshooting

### psycopg2 no encontrado

Superset usa un virtualenv interno en `/app/.venv/`. El `Dockerfile` personalizado instala `psycopg2-binary` a nivel sistema y lo copia al venv:

```dockerfile
FROM apache/superset:latest
USER root
RUN pip install psycopg2-binary && \
    cp -r /usr/local/lib/python3.10/site-packages/psycopg2* /app/.venv/lib/python3.10/site-packages/
USER superset
```

Si ya tienes el contenedor corriendo sin psycopg2, se puede instalar manualmente:

```bash
docker exec -u root bi-superset bash -c "
  pip install psycopg2-binary && 
  cp -r /usr/local/lib/python3.10/site-packages/psycopg2* /app/.venv/lib/python3.10/site-packages/
"
```

### Charts sin datos / errores de métricas

Los charts creados vía API necesitan métricas con **labels explícitos** para evitar conflictos con las columnas de groupby. El formato correcto es:

```json
{
  "metrics": [{
    "expressionType": "SIMPLE",
    "column": {"column_name": "defuncion"},
    "aggregate": "SUM",
    "label": "Total Defunciones"
  }],
  "columns": ["anio_ocurrencia"],
  "time_range": "No filter"
}
```

**NUNCA usar métricas como strings** (`"SUM(defuncion)"`) — causan errores de "Duplicate column/metric labels".

### Errores de "Datetime column not provided"

Ocurre en charts de tipo time-series que no tienen `time_range` configurado. Solución: agregar `"time_range": "No filter"` en `params` y `query_context`.

### Búsquedas API (search queries)

La API de Superset v4/v5 no soporta el parámetro `q` con formato de búsqueda entre paréntesis. En su lugar, se obtiene la lista completa de recursos y se filtra por nombre:

```python
# ❌ No funciona
resp = api_get(session, "/api/v1/chart/", params={"q": '(slice_name:"Mi Chart")'})

# ✅ Correcto
resp = api_get(session, "/api/v1/chart/")
for chart in resp.json()["result"]:
    if chart["slice_name"] == "Mi Chart":
        return chart["id"]
```

### Position JSON para dashboards

El formato correcto para Superset v5+ requiere `DASHBOARD_VERSION_KEY`, `children: []` en nodos CHART, y UUIDs reales de charts:

```json
{
  "DASHBOARD_VERSION_KEY": "v2",
  "ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
  "GRID_ID": {"id": "GRID_ID", "type": "GRID", "children": ["ROW-abc123"]},
  "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": "Overview"}},
  "ROW-abc123": {
    "id": "ROW-abc123", "type": "ROW", "children": ["CHART-xyz789"],
    "meta": {"background": "BACKGROUND_TRANSPARENT"},
    "parents": ["ROOT_ID", "GRID_ID"]
  },
  "CHART-xyz789": {
    "id": "CHART-xyz789", "type": "CHART", "children": [],
    "meta": {"chartId": 1, "height": 50, "width": 6, "uuid": "<chart-real-uuid>"},
    "parents": ["ROOT_ID", "GRID_ID", "ROW-abc123"]
  }
}
```

### Creación programática de dashboards

La REST API permite crear charts, datasets y dashboards. En esta implementación, `bi/setup/post_setup.py` actualiza el `position_json` con UUIDs reales de charts y aplica un pequeño throttle para evitar `429 Too Many Requests` de Superset.

Si se requiere portabilidad entre instancias, también se puede usar export/import ZIP:

1. Exportar todos los assets: `GET /api/v1/assets/export/`
2. Construir un ZIP con la estructura correcta de carpetas (`dashboard_export_<ts>/dashboards/...yaml`, `.../charts/...yaml`, etc.)
3. El metadata.yaml debe tener timestamp ISO 8601: `timestamp: '2026-06-25T14:49:02.155149+00:00'`
4. Importar: `POST /api/v1/dashboard/import/` con el ZIP como `multipart/form-data`

Ver `bi/setup/export_dashboards.py` para el script de exportación.

## Dashboards Creados

### Dashboard 1 — Pre vs Post COVID — Guatemala (ID: 1)

6 charts consumiendo `v_ine_completa` y `v_mspas_nacional`:

| Chart | Viz | Métrica | Valor |
|-------|-----|---------|-------|
| Total Defunciones Pre-COVID (2015-2019) | Table | SUM(defuncion) | 413,567 |
| Total Defunciones Post-COVID (2020-2024) | Table | SUM(defuncion) | 505,200 |
| Variación Pre vs Post COVID | Table | Custom SQL | +22.16% |
| Defunciones Mensuales 2015-2024 | Area Chart | SUM(defuncion) | — |
| Defunciones por Año — Pre vs Post COVID | Bar Chart | SUM(defuncion) | — |
| Tasa MSPAS x 100k hab | Line Chart | AVG(tasa_por_100k) | — |

### Dashboard 2 — Causas de Muerte (ID: 2)

4 charts consumiendo `v_ine_completa` y `v_ihme_centroamerica`:

| Chart | Viz | Métrica |
|-------|-----|---------|
| Defunciones por Causa GBD L2 | Treemap | SUM(defuncion) |
| Top 10 Causas de Muerte | Treemap | SUM(defuncion) |
| Tendencia Pre vs Post COVID | Line Chart | SUM(defuncion) |
| Tendencia de Causas en Centroamérica (IHME) | Line Chart | SUM(valor) |

### Dashboard 3 — Geografía y Demografía (ID: 3)

4 charts consumiendo `v_ine_completa`:

| Chart | Viz | Métrica |
|-------|-----|---------|
| Defunciones por Departamento | Treemap | SUM(defuncion) |
| Defunciones por Grupo Etario y Año | Stacked Bar | SUM(defuncion) |
| Resumen: Departamento × Causa | Pivot Table | SUM(defuncion) |
| Defunciones por Sexo y Año | Stacked Bar | SUM(defuncion) |

## Estructura de Archivos

```
bi/
├── docker-compose.yml              # Contenedor Superset + SQLite
├── Makefile                        # up/down/init/setup/status/export
├── config/
│   └── superset_config.py          # Configuración Python de Superset
├── geodata/
│   └── guatemala_departamentos.geojson  # 22 departamentos (WGS84)
├── dashboards/                     # ZIP + PNG exportados por make export
└── setup/
    ├── __init__.py
    ├── auth.py                     # JWT + CSRF authentication
    ├── client.py                   # Session manager + retry logic
    ├── database.py                 # get_or_create database connection
    ├── dataset.py                  # get_or_create datasets
    ├── chart.py                    # get_or_create charts
    ├── dashboard.py                # Dashboard creation + chart layout
    ├── config.py                   # 14 chart configs + DB/dataset configs
    ├── setup_superset.py           # Orquestador principal
    ├── export_dashboards.py        # Export ZIP + screenshots
    └── dashboards/
        ├── __init__.py
        ├── dash1_pre_post_covid.py
        ├── dash2_causas_muerte.py
        └── dash3_geografia_demografia.py
```

## Vistas SQL de Consumo

Para simplificar el consumo desde Superset, se crearon 4 vistas en el esquema `dm_mortality` que desnormalizan el esquema estrella:

| Vista | Fuente | Columnas | Filtro |
|-------|--------|----------|--------|
| `v_ine_completa` | `fact_ine` + 6 dims | 27 | Sin filtro (2015-2024 completo) |
| `v_mspas_nacional` | `fact_mspas` + 2 dims | 7 | `pais_iso3='GTM'` |
| `v_ihme_centroamerica` | `fact_ihme` + 5 dims | 12 | `metrica='Número'`, `medida='Deaths'`, 7 países CA |
| `v_poblacion_guatemala` | `fact_who_population` + 4 dims | 7 | `pais_iso3='GTM'` |

El script `sql/views_superset.sql` se ejecuta directamente contra Greenplum:

```bash
docker exec -i dw-greenplum psql -U gpadmin -d dw_semis2 < sql/views_superset.sql
```

## Interoperabilidad Demostrada

La plataforma cumple el requisito de interoperabilidad BI del enunciado:

1. **Mismo DW, dos herramientas**: Power BI y Superset consumen los mismos datos del Greenplum local
2. **Mismas vistas SQL**: Las vistas `v_*` en `dm_mortality` son compartidas por ambas herramientas
3. **API REST**: Superset expone una API completa que permite crear, modificar y exportar dashboards programáticamente (demostrando `HTTP/HTTPS` y `servicios web/APIs`)
4. **Exportación portable**: Los dashboards se exportan como ZIP que pueden importarse en cualquier instancia de Superset
