# Guía de backup y restore de Greenplum

Esta guía explica cómo validar un backup de Greenplum restaurándolo en una base separada de prueba y cómo hacer una exportación/restauración manual con SQL/`psql`.

> Recomendación: para pruebas, restaura siempre en una base temporal como `dw_semis2_restore_test`. No restaures encima de `dw_semis2` salvo que quieras reemplazar la base real.

## 1. Variables y ubicación

Desde la raíz del repositorio:

```bash
cd /Users/abdielo/dev/mortality-analytics
```

Si usas `.env`, carga las variables:

```bash
set -a
source .env
set +a
```

Valores esperados para el entorno local:

```bash
export GREENPLUM_CONTAINER=dw-greenplum
export GREENPLUM_DB=dw_semis2
export GREENPLUM_USER=gpadmin
export PGPASSWORD=semis2_grupo11
```

Los backups generados por `backup_greenplum.sh` quedan normalmente en:

```text
scripts/dw/backups/greenplum/
```

---

## 2. Crear un backup manual

```bash
cd scripts/dw
make backup
```

El script crea un archivo comprimido con formato:

```text
backups/greenplum/dw_semis2_YYYYMMDD_HHMMSS.dump.gz
```

Ejemplo para listar backups disponibles:

```bash
ls -lh backups/greenplum
```

---

## 3. Validar que el archivo no está corrupto

Elige un backup y valida el gzip:

```bash
gzip -t backups/greenplum/NOMBRE_DEL_BACKUP.dump.gz
```

Si el comando no imprime nada, el archivo comprimido está íntegro.

---

## 4. Restaurar en una base de prueba

### 4.1 Crear base temporal

Desde `scripts/dw`:

```bash
docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/dropdb \
  -h localhost \
  -U gpadmin \
  --if-exists \
  dw_semis2_restore_test

docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/createdb \
  -h localhost \
  -U gpadmin \
  dw_semis2_restore_test
```

### 4.2 Descomprimir backup a archivo temporal

```bash
gunzip -c backups/greenplum/NOMBRE_DEL_BACKUP.dump.gz > /tmp/dw_restore.dump
```

### 4.3 Restaurar con `pg_restore`

```bash
cat /tmp/dw_restore.dump | docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/pg_restore \
  -h localhost \
  -U gpadmin \
  -d dw_semis2_restore_test
```

Si termina sin errores, el backup pudo restaurarse correctamente.

---

## 5. Validar datos restaurados con SQL

Conectarse a la base original:

```bash
docker exec -it -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/psql \
  -h localhost \
  -U gpadmin \
  -d dw_semis2
```

Conectarse a la base restaurada:

```bash
docker exec -it -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/psql \
  -h localhost \
  -U gpadmin \
  -d dw_semis2_restore_test
```

Ejecuta esta consulta en ambas bases y compara los conteos:

```sql
SELECT 'dim_genero' AS table_name, COUNT(*) AS row_count FROM dm_mortality.dim_genero
UNION ALL
SELECT 'dim_geografia', COUNT(*) FROM dm_mortality.dim_geografia
UNION ALL
SELECT 'dim_causa', COUNT(*) FROM dm_mortality.dim_causa
UNION ALL
SELECT 'dim_etario', COUNT(*) FROM dm_mortality.dim_etario
UNION ALL
SELECT 'dim_source', COUNT(*) FROM dm_mortality.dim_source
UNION ALL
SELECT 'dim_tiempo', COUNT(*) FROM dm_mortality.dim_tiempo
UNION ALL
SELECT 'dim_ine_perfil', COUNT(*) FROM dm_mortality.dim_ine_perfil
UNION ALL
SELECT 'dim_ihme_perfil', COUNT(*) FROM dm_mortality.dim_ihme_perfil
UNION ALL
SELECT 'fact_ine', COUNT(*) FROM dm_mortality.fact_ine
UNION ALL
SELECT 'fact_mspas', COUNT(*) FROM dm_mortality.fact_mspas
UNION ALL
SELECT 'fact_who_deaths', COUNT(*) FROM dm_mortality.fact_who_deaths
UNION ALL
SELECT 'fact_who_population', COUNT(*) FROM dm_mortality.fact_who_population
UNION ALL
SELECT 'fact_panama', COUNT(*) FROM dm_mortality.fact_panama
UNION ALL
SELECT 'fact_ihme', COUNT(*) FROM dm_mortality.fact_ihme
ORDER BY table_name;
```

Resultado esperado si el backup es válido: los conteos de `dw_semis2` y `dw_semis2_restore_test` deben coincidir.

---

## 6. Restore real sobre la base principal

Usar solo si quieres reemplazar la base real `dw_semis2`.

```bash
cd scripts/dw

docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/dropdb \
  -h localhost \
  -U gpadmin \
  --if-exists \
  dw_semis2

docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/createdb \
  -h localhost \
  -U gpadmin \
  dw_semis2

gunzip -c backups/greenplum/NOMBRE_DEL_BACKUP.dump.gz > /tmp/dw_restore.dump

cat /tmp/dw_restore.dump | docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/pg_restore \
  -h localhost \
  -U gpadmin \
  -d dw_semis2
```

Después valida conteos con la consulta de la sección 5.

---

## 7. Backup manual con SQL/psql usando `COPY`

Esta alternativa no reemplaza `pg_dump`, pero sirve para demostrar backup/restauración manual de datos tabulares.

### 7.1 Crear carpeta de exportación

```bash
mkdir -p /tmp/greenplum_manual_backup
```

### 7.2 Exportar tablas a CSV desde psql

Ejemplo para una dimensión:

```bash
docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/psql \
  -h localhost \
  -U gpadmin \
  -d dw_semis2 \
  -c "COPY dm_mortality.dim_genero TO STDOUT WITH CSV HEADER" \
  > /tmp/greenplum_manual_backup/dim_genero.csv
```

Ejemplo para una tabla fact:

```bash
docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/psql \
  -h localhost \
  -U gpadmin \
  -d dw_semis2 \
  -c "COPY dm_mortality.fact_ine TO STDOUT WITH CSV HEADER" \
  > /tmp/greenplum_manual_backup/fact_ine.csv
```

### 7.3 Crear base vacía para restore manual

```bash
docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/dropdb \
  -h localhost \
  -U gpadmin \
  --if-exists \
  dw_semis2_manual_restore

docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/createdb \
  -h localhost \
  -U gpadmin \
  dw_semis2_manual_restore
```

Aplicar el DDL del proyecto:

```bash
docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/psql \
  -h localhost \
  -U gpadmin \
  -d postgres \
  -f - < init.sql
```

> Nota: `init.sql` crea/actualiza `dw_semis2`. Para una base manual diferente, puedes copiar el DDL y cambiar `\c dw_semis2;` por `\c dw_semis2_manual_restore;`, o restaurar manualmente dentro de `dw_semis2` si estás haciendo una prueba controlada.

### 7.4 Importar CSV manualmente

Primero trunca la tabla destino:

```bash
docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/psql \
  -h localhost \
  -U gpadmin \
  -d dw_semis2_manual_restore \
  -c "TRUNCATE TABLE dm_mortality.dim_genero"
```

Luego importa el CSV:

```bash
cat /tmp/greenplum_manual_backup/dim_genero.csv | docker exec -i -u gpadmin dw-greenplum \
  /usr/local/greenplum-db/bin/psql \
  -h localhost \
  -U gpadmin \
  -d dw_semis2_manual_restore \
  -c "COPY dm_mortality.dim_genero FROM STDIN WITH CSV HEADER"
```

Validar:

```sql
SELECT COUNT(*) FROM dm_mortality.dim_genero;
```

---

## 8. Qué método usar

- Para respaldo completo y restauración fiel: usa `backup_greenplum.sh` + `pg_restore`.
- Para demostrar export/import manual por tabla: usa `COPY TO STDOUT` y `COPY FROM STDIN`.
- Para pruebas de seguridad: restaura en una base temporal y compara conteos.
