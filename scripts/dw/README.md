# Data Warehouse local con Greenplum

Este directorio contiene la base local para Fase 2. Greenplum funciona como réplica local del modelo Fact-Dim cuya fuente de verdad será Databricks.

## Alcance actual

- Greenplum inicializa los schemas `dm_mortality`, `dm_stage` y `dm_meta`.
- `dm_mortality` contiene dimensiones y hechos del modelo dimensional.
- `dm_meta` registra auditoría de replicación y backups.
- La conexión real a Databricks queda pendiente hasta que el nuevo workspace esté disponible.

## Levantar Greenplum

```bash
cd scripts/dw
make up
```

## Variables operativas

```bash
export GREENPLUM_HOST=localhost
export GREENPLUM_PORT=5432
export GREENPLUM_DB=dw_semis2
export GREENPLUM_USER=gpadmin
export PGPASSWORD=semis2_grupo11
```

## Replicación Databricks → Greenplum

La estructura está preparada en `replication/`. La primera integración usa la Databricks Statement Execution API porque el conector Python SQL puede quedarse esperando en algunos entornos serverless. La prueba inicial replica `semi2.dm_mortality.dim_genero` con full refresh por ser una dimensión pequeña y ya disponible.

Ejecutar preflight:

```bash
make replication-preflight
```

Configurar Databricks:

```bash
export DATABRICKS_HOST="dbc-xxxx-xxxxx-xxxxx"
export DATABRICKS_HTTP_PATH="/sql/xxxxxxxxxx"
export DATABRICKS_TOKEN="dapiXXXXXXXXXXXXXXXX"
```

Instalar dependencias:

```bash
pip install -r ../../requirements.txt
```

Replicar solo `dim_genero`:

```bash
make replicate-dim-genero
```

Replicar todas las dimensiones configuradas en `tables.json`:

```bash
make replicate-dimensions
```

Replicar todas las tablas de hechos:

```bash
make replicate-facts
```

Replicar todo el Data Warehouse configurado:

```bash
make replicate-all
```

Probar todas las dimensiones con una carga limitada:

```bash
make replicate-dimensions-limit
```

Probar hechos o todo el DW con carga limitada:

```bash
make replicate-facts-limit
make replicate-all-limit
```

Probar solamente la conexión y consultas en Databricks:

```bash
make test-databricks
```

Replicar una muestra limitada para validar conectividad antes del full refresh:

```bash
make replicate-dim-tiempo-limit
```

El flujo ejecuta consultas REST contra Databricks, trunca la tabla equivalente en Greenplum, carga los datos por `COPY` y registra conteos en `dm_meta.replication_table_checks`.
Para cargas completas usa `EXTERNAL_LINKS` en la Statement Execution API, evitando el límite de resultados inline de Databricks.
Antes de truncar/cargar una tabla completa, valida que las filas descargadas coincidan con `COUNT(*)` en Databricks; si hay diferencia, falla sin reemplazar la tabla local.

Las tablas grandes pueden declararse con `partition_column` en `replication/tables.json`. Actualmente `fact_ine` se descarga por rangos de `id_tiempo` de 20 en 20 para evitar resultados parciales en respuestas grandes de Databricks sin hacer una consulta por cada valor individual.

## Réplica condicional por tabla de control

Para no replicar de forma ciega cada pocos minutos, Databricks puede registrar el fin exitoso del pipeline en una tabla de control y Greenplum solo hará pull cuando detecte un `run_id` nuevo.

### Tabla de control en Databricks

Crear una vez en Databricks:

```sql
CREATE SCHEMA IF NOT EXISTS workspace.dm_meta;

CREATE TABLE IF NOT EXISTS workspace.dm_meta.pipeline_runs (
  run_id STRING,
  pipeline_name STRING,
  status STRING,
  completed_at TIMESTAMP,
  source STRING,
  notes STRING
);
```

`run_id` debe ser único por ejecución de pipeline. El checker local usa ese valor para decidir si una corrida ya fue replicada.

Al final del pipeline Databricks, insertar un registro exitoso:

```sql
INSERT INTO workspace.dm_meta.pipeline_runs
VALUES (
  concat('mortality_pipeline_', date_format(current_timestamp(), 'yyyyMMddHHmmss')),
  'mortality_etl_pipeline',
  'SUCCESS',
  current_timestamp(),
  'databricks',
  'Pipeline completed successfully'
);
```

El nombre del pipeline se puede ajustar con:

```bash
export DATABRICKS_PIPELINE_NAME=mortality_etl_pipeline
export DATABRICKS_PIPELINE_RUNS_TABLE=workspace.dm_meta.pipeline_runs
```

### Registro local en Greenplum

Greenplum usa `dm_meta.processed_pipeline_runs` para recordar cuáles `run_id` ya fueron replicados y evitar reprocesarlos en cada cron.

Si la base ya estaba levantada antes de este cambio, volver a aplicar el DDL:

```bash
cd scripts/dw
docker exec -i -u gpadmin dw-greenplum /usr/local/greenplum-db/bin/psql -h localhost -U gpadmin -d postgres -f - < init.sql
```

### Checker local

El checker revisa el último registro `SUCCESS` en Databricks y ejecuta `make replicate-all` solo si ese `run_id` no existe como `replicated` en Greenplum. Como la réplica es full refresh, se replica el último estado exitoso disponible; si el cron estuvo apagado y hubo varias corridas exitosas, las corridas intermedias no se replican individualmente.

Estados locales en `dm_meta.processed_pipeline_runs`:

- `replicated`: la réplica completa terminó sin inconsistencias.
- `partial`: algunas tablas cargaron y otras fallaron o se omitieron; el cron no reintenta automáticamente ese `run_id`.
- `failed`: no se pudo completar una réplica útil; el cron no reintenta automáticamente ese `run_id`.
- `test_only`: se ejecutó una carga limitada de prueba; no cuenta como réplica completa.
- `retry_requested`: permite reintentar manualmente un `run_id` que había quedado `partial` o `failed`.

Si quieres reintentar manualmente una corrida parcial/fallida:

```sql
UPDATE dm_meta.processed_pipeline_runs
SET replication_status = 'retry_requested'
WHERE run_id = 'mortality_pipeline_...';
```

La réplica intenta continuar por tabla, pero trata el bloque de dimensiones como una unidad atómica: si una dimensión falla, se revierte la carga de dimensiones de esa corrida y los hechos se omiten con `skipped_dependency` para evitar facts cargados contra dimensiones incompletas. Si falla un fact, los demás facts independientes pueden continuar. Las cargas parciales quedan auditadas en `dm_meta.replication_table_checks`.

Si un proceso muere dejando un run en `running`, el checker lo considera reintentable después de `GREENPLUM_STALE_RUNNING_MINUTES` minutos. El valor por defecto es `120`.

Prueba sin ejecutar réplica ni cambiar estado:

```bash
make check-pipeline-runs-dry-run
```

Ejecución real:

```bash
make check-pipeline-runs
```

También se puede cambiar el target de réplica para pruebas:

```bash
export GREENPLUM_REPLICATION_MAKE_TARGET=replicate-all-limit
make check-pipeline-runs
```

Los targets `*-limit` son destructivos porque truncan tablas y cargan solo una muestra. Úsalos únicamente para pruebas. El checker los marca como `test_only`, no como `replicated`.

## Backup manual

```bash
make backup
```

El backup usa `pg_dump -Fc`, lo comprime con gzip y elimina backups antiguos según `GREENPLUM_BACKUP_RETENTION_DAYS`.
Si el host no tiene `pg_dump`, el script usa `docker exec` contra el contenedor `dw-greenplum` y escribe el dump en el host.

Guía completa para validar y restaurar backups en una base separada: [`BACKUP_RESTORE_GUIDE.md`](./BACKUP_RESTORE_GUIDE.md).

Variable opcional para cambiar el contenedor:

```bash
export GREENPLUM_CONTAINER=dw-greenplum
export GREENPLUM_CONTAINER_PG_DUMP=/usr/local/greenplum-db/bin/pg_dump
```

## Cron sugerido

### Réplica Databricks → Greenplum

El script `check_and_replicate_cron.sh` carga variables desde `.env`, activa `.venv` si existe y ejecuta el checker condicional. Si hay un pipeline nuevo exitoso en `workspace.dm_meta.pipeline_runs`, entonces dispara `make replicate-all`.

Para pruebas cada 5 minutos:

```cron
PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin

*/5 * * * * /Users/abdielo/dev/mortality-analytics/scripts/dw/check_and_replicate_cron.sh >> /tmp/greenplum_replication.log 2>&1
```

Ejemplo diario a la 1:00 AM:

```cron
0 1 * * * /Users/abdielo/dev/mortality-analytics/scripts/dw/check_and_replicate_cron.sh >> /tmp/greenplum_replication.log 2>&1
```

El archivo `.env` debe contener, como mínimo:

```bash
DATABRICKS_HOST=...
DATABRICKS_HTTP_PATH=...
DATABRICKS_TOKEN=...
DATABRICKS_PIPELINE_NAME=mortality_etl_pipeline
DATABRICKS_PIPELINE_RUNS_TABLE=workspace.dm_meta.pipeline_runs
GREENPLUM_HOST=localhost
GREENPLUM_PORT=5432
GREENPLUM_DB=dw_semis2
GREENPLUM_USER=gpadmin
PGPASSWORD=...
```

### Backup Greenplum

```cron
0 2 * * * cd /Users/abdielo/dev/mortality-analytics/scripts/dw && . /Users/abdielo/dev/mortality-analytics/.env && ./backup_greenplum.sh >> /tmp/greenplum_backup.log 2>&1
```

La réplica se agenda antes del backup para que el respaldo capture el estado más reciente del DW local.

## Pendientes

- Confirmar nombres finales de tablas Fact-Dim en Databricks.
- Confirmar si solo se replica `dm_mortality` o también `stage`.
- Decidir si se sube la auditoría `dm_meta` de vuelta a Databricks como evidencia de interoperabilidad inversa.
- Extender la replicación validada de `dim_tiempo` al resto de tablas del manifest.
