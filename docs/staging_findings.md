# Hallazgos y correcciones — Capa de Staging

Diagnóstico y resolución de problemas encontrados al ejecutar los notebooks de
sandbox y staging en Databricks. Incluye bugs de infraestructura, decisiones de
alcance, coberturas de normalización y estado final de cada tabla.

> **Fecha de última revisión:** 2026-06-18. Las coberturas y conteos reflejan
> las tablas `stage.*` reales en Databricks (no exports CSV truncados).

---

## 1. Decisiones de alcance (stage)

### MSPAS exceso — ELIMINADO (definitivo)

`stage.mspas_exceso` se retira del alcance. Motivos:
- La fuente solo cubre **2022**, fuera del enfoque pre/post-COVID (2015–2022).
- La columna `grupo` combinaba dos particiones independientes (edad `<65`/`>65`
  y sexo `Hombres`/`Mujeres`) más `Total` en una sola columna de texto. Eran
  totales marginales solapados, no un cruce real → no modelables sin doble conteo.

**Acción ejecutada:**
- `notebooks/staging/mspas.py`: eliminados `SCHEMA_EXCESO`, `_rename_exceso`,
  `transform_exceso` y el bloque `try` que escribía `stage.mspas_exceso`.
- `notebooks/sandbox/rds_mspas_guatemala_ingest.py`: removido el mapeo
  `raw_data.mspas_exceso_mortalidad_2022 → sandbox.raw_mspas_exceso`.
- El notebook ahora solo procesa `mspas_mortalidad_general` y `mspas_tasa`.

### IHME — columnas CIE-10 eliminadas

IHME viene con la causa ya agregada a **GBD Nivel 2** (ej. `Neoplasms`), que
corresponde a un rango de ~100+ códigos CIE-10. El mapeo es muchos-a-uno y **no
reversible**: dado "Neoplasms" no se sabe si fue C50 (mama) o C34 (pulmón). Por
eso `cie10_code` y `cie10_nombre` no aplican y se eliminaron del schema, la
función `_add_gbd_columns` y el `select` final de `staging/ihme.py`.

### `area_geografica` (INE) — descartada, no validada

El esquema original del INE traía `Areag` (área geográfica). Se decidió
**dropearla** (`_INE_DROP_COLS`), alineado con §3.1 del modelo dimensional
(simplificación de geografía a solo ocurrencia: dep/mun). La sección anterior
de este doc que describía `_validate_area_geografica` queda obsoleta.

---

## 2. Bugs de infraestructura — Databricks Connect

### 2.1 Split-brain: `file:` scheme no resuelve en el cluster

**Síntoma:** los notebooks de ingesta (gDrive) descargan archivos CSV al
filesystem del cliente, pero `spark.read.format("csv").load("file:/Workspace/...")`
falla con `PATH_NOT_FOUND` o lee DataFrames vacíos.

**Causa:** el proyecto usa **Databricks Connect** (el cliente Python corre
local; el cluster Spark corre remoto). `file:` scheme busca en el filesystem
del **cluster**, donde los archivos descargados por Python nunca llegaron. Solo
los archivos cacheados de corridas previas funcionaban (falsa apariencia de
éxito).

**Impacto medido en INE:** `sandbox.raw_ine` quedó con solo 4,126 filas de 2
archivos (2021, 2023 — cacheados) en lugar de los ~920k esperados de 10
archivos (2015–2024). Esto a su vez hacía que la cobertura GBD se midiera sobre
un sample no representativo.

**Corrección:** migrar todas las lecturas de CSV al patrón **pandas en cliente
+ `spark.createDataFrame(pdf)`**. Los datos viajan por el protocolo de Connect,
sin tocar el FS del cluster.

```python
import pandas as pd
pdf = pd.read_csv(final_path, dtype=str, keep_default_na=False, encoding="utf-8")
df = spark.createDataFrame(pdf).withColumn(...)
```

**Archivos fixeados:**
- `gdrive_ine_guatemala_ingest.py`: bucle de 10 CSV de defunciones + diccionario
  de defunciones + diccionario CIE-10.
- `gdrive_sandbox_ingest.py` (duplicado idéntico): mismo fix.

### 2.2 Naming de columnas: `_c0` vs `0, 1, 2`

**Síntoma:** `staging/ine.py` lanza
`[UNRESOLVED_COLUMN.WITH_SUGGESTION] A column, variable, or function parameter with name '_c0' cannot be resolved. Did you mean one of the following? [0, 1, 2, ...]`.

**Causa:** `pd.read_csv(..., header=None)` nombra las columnas con enteros
`0, 1, 2`, pero `_load_catalogs()` busca `_c0, _c1, _c2` (la convención que
`spark.read.csv` sin header generaba). Al migrar a pandas se perdió el naming.

**Corrección:** renombrar las columnas del DataFrame de pandas antes de
`spark.createDataFrame`:

```python
pdf.columns = [f"_c{i}" for i in range(len(pdf.columns))]
```

### 2.3 Truncado de `display()` confunde el análisis

**Síntoma:** el CSV exportado `INE-5.csv` tenía 4,217 filas y solo 3 años
(2017, 2019, 2023), sugiriendo que la ingesta falló.

**Causa:** `display(df)` en Databricks trunca la preview a ~4,000 filas. El CSV
se exportó desde esa preview, no desde la tabla real. La tabla `stage.ine`
sí tenía los 918,687 filas completas.

**Lección:** validar conteos siempre con `spark.read.table("stage.ine").count()`
o agregaciones, nunca con el truncado de `display()`.

---

## 3. Hallazgos por fuente

### 3.1 INE (`notebooks/staging/ine.py`)

#### `asistencia_medica` — corregido (100% null → poblado)

El schema original definía `asistencia_medica` como `BooleanType`, pero los CSV
del INE traen códigos numéricos (`1`–`5`, `9`) o etiquetas (`Médica`, `Empírica`).
El cast fallaba silenciosamente. Corregido a `StringType` + decodificación vía
catálogo. Distribución final en stage:

| Valor | Filas | % |
|---|---|---|
| Médica | 2464 | 58.0% |
| Ninguna | 1547 | 36.4% |
| Empírica | 96 | 2.3% |
| Paramédica | 17 | 0.4% |
| Comadrona | 1 | 0.0% |
| null | 120 | 2.8% |

#### `cie10_nombre` — poblado desde diccionario CIE-10 del INE

Antes `cie10_nombre` era NULL por diseño (el master GBD no trae el nombre de
cada código CIE-10). Se cableó al diccionario CIE-10 del INE
(`data/raw/ine/csv/ine_diccionario_cie-10.csv`, 14,365 filas, código →
descripción en español). Cobertura final: **100%** (4,217/4,217 en sample,
918,687/918,687 en tabla real).

**Infraestructura requerida:** el diccionario se ingesta a
`sandbox.raw_ine_diccionario_cie10` desde gDrive (mismo patrón pandas +
createDataFrame).

#### Crosswalk etario — implementado

INE trae año simple `edad` (0–120) + `periodo_edad` para <1 año. Se derivan
`id_etario` + `categoria_etaria` vía `_add_etario_columns` (crosswalk §5.3 del
modelo dimensional). Cobertura: **100%**. Distribución real (tabla de 918k):

| id_etario | Banda | Categoria | % aprox |
|---|---|---|---|
| 1 (LT1) | Menores de 1 | Niñez | ~3% |
| 2 (01-04) | 1 a 4 | Niñez | ~2% |
| 5-7 (15-29) | Juventud | Juventud | ~6% |
| 8-14 (30-64) | Adultez | Adultez | ~45% |
| 15-19 (65+) | Vejez | Vejez | ~42% |
| 98 (UNK) | No especificada | — | ~0.5% |

### 3.2 IHME (`notebooks/staging/ihme.py`)

#### `medida` — corregido (50% null → 0% null)

Los datos raw incluyen el nombre completo entre paréntesis:
`"DALYs (Disability-Adjusted Life Years)"`. El `isin` contra
`MEDIDAS_VALIDAS` no encontraba coincidencia. Corregido con `regexp_replace`
que elimina el paréntesis antes de validar.

Distribución final: `Deaths` 2,592 + `DALYs` 2,592 = 5,184 filas. `metrica`:
`Número` 1,728 + `Tasa` 1,728 + `Porcentaje` 1,728.

#### Cobertura GBD y etario

| Métrica | Cobertura |
|---|---|
| `gbd_code` NOT null | 5,184 / 5,184 (**100%**) |
| `id_etario` NOT null | 5,184 / 5,184 (**100%**) |
| `id_etario` valor único | `99` (ALL/Total) — correcto, IHME solo trae "All ages" |

#### Cobertura temporal

Años 2015–2023 (9 años). Todas las causas son GBD Nivel 2 nativas (16 causas).

### 3.3 MSPAS (`notebooks/staging/mspas.py`)

#### Contexto: los "Excel" de MSPAS son PDFs con gráficas

Los archivos fuente resultaron ser PDFs con imágenes, no tablas estructuradas.
La extracción solo capturó totales anuales. Schemas simplificados a lo disponible.

#### Estado final (tras eliminar exceso)

| Tabla | Filas | Años | Columnas |
|---|---|---|---|
| `stage.mspas_mortalidad_general` | 15 | 2010–2024 | 6 (`anio`, `defunciones`, ...) |
| `stage.mspas_tasa` | 19 | 2001–2019 | 6 (`anio`, `tasa_por_100k`, ...) |

Total defunciones (general): 1,291,799. Tasa cubre solo pre-COVID (acaba 2019).

### 3.4 Panamá (`notebooks/staging/panama.py`)

#### Cobertura GBD y etario

| Métrica | Cobertura |
|---|---|
| `gbd_code` NOT null | 4,103 / 5,592 (**73.4%**) |
| `id_etario` NOT null | 5,592 / 5,592 (**100%**) |
| `nivel` (anti doble-conteo) | simple 5,411 + grupo 181 |

Cobertura temporal: 2020–2024 (4 años en el output actual; la raw tiene 2015–2024).

### 3.5 WHO (`notebooks/staging/who_mortality.py`)

#### Cobertura temporal (corrección del doc)

`WHO.csv` (deaths) y `WHO-2.csv` (population) cubren **2015–2022 completo**
(8 años), no 2000–2003 como decía `modelo_dimensional.md` §2.2. WHO se
mantiene como hecho válido.

| Tabla | Filas | Años | age_group_code |
|---|---|---|---|
| `WHO.csv` (deaths) | 1,344 | 2015–2022 | 21 bandas (all, 0, 1-4, ... 85+, age_unknown) |
| `WHO-2.csv` (population) | 672 | 2015–2022 | 28 bandas (incluye agregados solapados) |

#### Pendiente: normalización GBD + etario + descarte de bandas solapadas

WHO aún **no** tiene columnas `gbd_*` ni `id_etario` (el notebook no se tocó en
esta ronda). Pendiente:
- `indicator_code` (CGXXXX) → `gbd_code` directo (WHO lo usa nativamente).
- `age_group_code` → `id_etario` vía crosswalk §5.3.
- Descartar agregados solapados de population: `age00_04`, `age05_14`,
  `age15_24`, `age25_34`, `age35_54`, `55-74`, `75+` (§5.4 #1).

---

## 4. Cobertura de normalización GBD — INE (detalle)

### 4.1 El problema: gaps del master GBD

El crosswalk CIE-10 → GBD Nivel 2 se construye desde los rangos ICD-10 del
master GBD (`Deaths.XLSX`, 811 códigos de 3 chars con dueño único). Sin
embargo, el master deja **gaps** que excluyen códigos CIE-10 muy comunes en
Guatemala:

| Código CIE-10 | Descripción | Filas (10 años) | Gap del master |
|---|---|---|---|
| `J18` | Neumonía | 56,507 | Rango J09-J15.8 deja fuera J16-J19 |
| `E14` | Diabetes no insulinodependiente | 55,930 | Solo E10-E11 en el master |
| `R99` | Causa mal definida | 42,408 | Fuera de las 16 (correcto NULL) |
| `R98` | Muerte sin asistencia | 34,175 | Fuera de las 16 (correcto NULL) |
| `X59` | Exposición no especificada | 27,952 | Gap X54.9-X57 |
| `R54` | Senilidad | 27,801 | Fuera de las 16 (correcto NULL) |
| `I64` | AVC no especificado | 17,499 | Gap I63.9-I65 |
| `V89` | Accidente vehículo no espec. | 16,958 | Gap V86.9-V87.2 |
| `I50` | Insuficiencia cardíaca | 14,217 | Gap I48.9-I51.0 |
| `A41` | Sepsis | 12,397 | Fuera de las 16 |
| `N19` | Insuficiencia renal | 11,505 | Solo N18 en el master |
| `I10` | Enfermedad hipertensiva | 9,613 | Solo I11 en el master |

### 4.2 Cobertura antes y después de los overrides

| Escenario | Filas con causa | Cobertura |
|---|---|---|
| Crosswalk original (811 códigos) | 445,688 / 919,231 | **48.5%** |
| + Overrides (22 códigos → 16 causas) | 667,331 / 919,231 | **72.6%** |
| + Nombres fuera de las 16 (12 códigos) | 711,611 / 919,231 | **77.4%** |
| R-codes (mal definidos, NULL correcto) | 124,564 / 919,231 | 13.6% |
| Resto sin causa (NULL) | 83,056 / 919,231 | 9.0% |

### 4.3 Overrides aplicados (22 códigos → 16 causas GBD)

Códigos de 3 chars que el master deja en gaps pero que lógicamente pertenecen
a una de las 16 causas (verificación manual vs WHO Mortality):

| CIE-10 | Causa GBD asignada | Filas |
|---|---|---|
| `I10`, `I50`, `I64`, `I26`, `I99` | Cardiovascular diseases | ~45k |
| `E14`, `N17`, `N19`, `N39` | Diabetes and kidney diseases | ~83k |
| `J18`, `J96` | Respiratory infections and tuberculosis | ~59k |
| `V89` | Transport injuries | ~17k |
| `X45`, `X49`, `X59`, `W76` | Unintentional injuries | ~37k |
| `K72`, `K65` | Digestive diseases | ~4k |
| `Y09` | Self-harm and interpersonal violence | ~2k |
| `C80`, `C55`, `C74` | Neoplasms | ~10k |

### 4.4 Causas fuera de las 16 (12 códigos → solo `gbd_nombre`)

Códigos que pertenecen a causas GBD Nivel 2 fuera de las 16. Se puebla **solo**
`gbd_nombre` (autoritativo); `gbd_code`/`gbd_cause_id` quedan NULL porque el
`CGxxxx` no existe en ninguna fuente confiable (no se fabrica). Misma regla
que Panamá lista-103 (§6.4):

| CIE-10 | gbd_nombre | Filas |
|---|---|---|
| `A41` | Other infectious diseases | ~12k |
| `F10` | Substance use disorders | ~5k |
| `P07`, `P21`, `P22`, `P24`, `P36` | Neonatal disorders | ~17k |
| `Q24`, `Q89`, `Q90` | Congenital birth defects | ~9k |
| `D64`, `D65` | Blood disorders | ~5k |
| `E86`, `E87` | Nutritional deficiencies | ~6k |

### 4.5 Cobertura GBD por año (tabla real `stage.ine`, 918,687 filas)

| Año | Filas | `gbd_code` NOT null | Cobertura |
|---|---|---|---|
| 2015 | 80,814 | 63,127 | 78.1% |
| 2016 | 82,521 | 63,635 | 77.1% |
| 2017 | 81,665 | 62,512 | 76.5% |
| 2018 | 83,021 | 62,557 | 75.4% |
| 2019 | 85,518 | 64,323 | 75.2% |
| 2020 | 95,955 | 74,095 | 77.2% |
| 2021 | 118,414 | 92,064 | 77.7% |
| 2022 | 95,337 | 70,428 | 73.9% |
| 2023 | 95,889 | 69,642 | 72.6% |
| 2024 | 99,553 | 71,772 | 72.1% |

Tendencia: ligera caída en 2022–2024, posiblemente por mayor proporción de
códigos mal definidos (R-codes) en años recientes.

---

## 5. Crosswalk etario — implementación por fuente

Grid canónico `DIM_ETARIO` (§5.2 del modelo dimensional): 21 filas (id_etario
1–19 + 98 UNK + 99 ALL). Cada notebook embebe el grid y deriva `id_etario` +
`categoria_etaria` (Niñez/Juventud/Adultez/Vejez/Total para roll-up).

| Fuente | Cómo deriva `id_etario` | Cobertura |
|---|---|---|
| **INE** | año simple `edad` → banda (`F.when` encadenado); null → 98 (UNK) | 100% |
| **Panamá** | etiqueta normalizada → mapa directo (`'Menores de 1'`→1, …, `'No especificada'`→98) | 100% |
| **IHME** | `'All ages'` → 99 (ALL/Total), miembro único | 100% |
| **WHO** | pendiente (`age_group_code` → `id_etario`) | — |
| **MSPAS** | no aplica (sin edad, solo totales nacionales) | — |

MSPAS no recibe `id_etario` porque sus tablas son totales anuales sin
desglose etario.

---

## 6. Estado final de schemas

### `stage.ine` — 41 columnas, 918,687 filas

Cobertura: años 2015–2024 (10), `gbd_code` 75% promedio, `cie10_nombre` 100%,
`id_etario` 100%. Incluye `id_etario` + `categoria_etaria` + bloque
`cie10_*`/`gbd_*` completo.

### `stage.ihme` — 23 columnas, 5,184 filas

Cobertura: años 2015–2023, `gbd_code` 100%, `id_etario` 100% (todo 99/ALL).
Sin `cie10_*` (no aplica). `medida`/`metrica` corregidas.

### `stage.panama` — 23 columnas, 5,592 filas

Cobertura: `gbd_code` 73.4%, `id_etario` 100%, `nivel` (anti doble-conteo)
presente. Bloque `cie10_*`/`gbd_*` completo.

### `stage.mspas_mortalidad_general` — 6 columnas, 15 filas

Años 2010–2024. Solo `anio` + `defunciones` (totales nacionales).

### `stage.mspas_tasa` — 6 columnas, 19 filas

Años 2001–2019. Solo `anio` + `tasa_por_100k` (por-100k). NULL para 2020–2024
(documentar en dashboards pre/post-COVID).

### `stage.mspas_exceso` — ELIMINADO

No se genera. El notebook ya no lo procesa.

---

## 7. Patrones reutilizables identificados

### pandas + `spark.createDataFrame` (Databricks Connect)

Para leer CSV locales en un entorno con Databricks Connect, **nunca** usar
`spark.read.format("csv").load("file:...")` (busca en el FS del cluster
remoto). En su lugar, leer con pandas en el cliente y enviar al cluster:

```python
import pandas as pd
pdf = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
pdf.columns = [f"_c{i}" for i in range(len(pdf.columns))]  # si se espera _c0,_c1,...
df = spark.createDataFrame(pdf).withColumn(...)
```

Válido para archivos de hasta ~hundreds of MB (limitado por el overhead del
protocolo de Connect).

### `_normalize_cols` — renombrar + completar con nulls

Cuando la fuente puede tener nombres en inglés o en español, y puede carecer
de columnas opcionales:

```python
def _normalize_cols(df, rename_map, null_defaults):
    select_exprs = []
    seen = set()
    for c in df.columns:
        target = rename_map.get(c, c)
        if target not in seen:
            select_exprs.append(F.col(f"`{c}`").alias(target))
            seen.add(target)
    df = df.select(*select_exprs)
    for col, dtype in null_defaults.items():
        if col not in df.columns:
            df = df.withColumn(col, F.lit(None).cast(dtype))
    return df
```

### Backtick escaping para palabras reservadas SQL

PySpark `withColumnRenamed("group", "grupo")` falla con palabras reservadas.
La forma correcta:

```python
F.col("`group`").alias("grupo")
```

### Sentinels: blancos del raw → null en staging

El raw rellena blancos con `"Desconocido"` / `"No Especificado"` / `"Ignorado"`
para evitar nulls en Delta. El staging los revierte a `null` con
`_apply_sentinels`. Si una columna nueva tiene este comportamiento, agregarla
a `_SENTINEL_COLS`.

---

## 8. Pendientes

| # | Tema | Estado |
|---|---|---|
| 1 | WHO: aplicar GBD (`indicator_code`→`gbd_code`) + etario + descartar bandas solapadas | Pendiente |
| 2 | WHO: eliminar agregados solapados de population (`age00_04`, `55-74`, `75+`, etc.) | Pendiente |
| 3 | Regenerar `ddl.sql` desde los schemas reales (actual está stale) | Pendiente |
| 4 | Capa dimensional: `DIM_CAUSA`, `DIM_ETARIO`, `DIM_TIEMPO`, `DIM_GEOGRAFIA`, `DIM_SOURCE` | Pendiente |
| 5 | Capa de hechos: `FACT_INE`, `FACT_PANAMA`, `FACT_IHME`, `FACT_MSPAS`, `FACT_WHO_*` | Pendiente |
| 6 | Actualizar `modelo_dimensional.md` §2.2 (WHO cubre 2015–2022, no 2000–2003) | Pendiente |
