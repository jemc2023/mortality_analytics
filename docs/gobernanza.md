# Gobernanza de Datos

> Fuente de verdad operacional: las fuentes, reglas de limpieza y niveles de agregación descritos aquí corresponden a los procesos implementados en `notebooks/`.

---

## Catálogo de Metadatos

Inventario de todos los conjuntos de datos del proyecto con sus atributos de origen, cobertura y clasificación.

| ID | Fuente | Publicador | Licencia | Tipo | Sensibilidad | Tabla Delta |
|----|--------|-----------|----------|------|-------------|-------------|
| DS-01 | INE Guatemala — defunciones | INE GT | Datos abiertos | Microdato | Alta | `sandbox.raw_ine` |
| DS-02 | MSPAS — estadísticas vitales | MSPAS GT | Datos abiertos | Agregado | Baja | `sandbox.raw_mspas_*` |
| DS-03 | IHME GBD 2023 | IHME / U. Washington | No comercial | Estimación | Baja | `sandbox.raw_ihme` |
| DS-04 | Panamá INEC | INEC Panamá | Datos abiertos | Agregado | Baja | `sandbox.raw_panama*` |
| DS-05 | WHO Mortality DB | OMS | CC BY-NC-SA 3.0 IGO | Agregado | Baja | `sandbox.raw_who_mortality_*` |
| DS-06 | PAHO Core Indicators | OPS | CC BY | Indicadores | Baja | Pendiente |
| DS-07 | INEC Costa Rica | INEC CR | Uso público (PAD5) | Microdato | Media | Pendiente |
| DS-08 | RENAP Guatemala | RENAP GT | Solicitud formal | Microdato | Alta (potencial) | Pendiente |

### Almacenamiento por capa

| Capa | Tecnología | Ubicación |
|------|-----------|-----------|
| Archivos GT/INE | Google Drive | `semis2_raw_data/ine/` |
| Archivos Panamá | OneDrive | `semi2-mortalidad/panama/` |
| Archivos WHO | nginx (DevTunnel) | Servidor local |
| Objetos S3 | AWS S3 | `s3://mortality-analytics-semi2/raw/` |
| Base relacional | RDS PostgreSQL | Schema `raw_data`, DB `mortality_dw` |
| Data Lake | Databricks Delta Lake | Schema `sandbox.*` |

---

## Plan de Anonimización

### Marco regulatorio

El proyecto opera en contexto académico con datos de salud pública. Para la fase de ingesta y publicación interna en Sandbox, la referencia principal es el **EU Data Act (Reglamento UE 2023/2854)** en cuanto a interoperabilidad, portabilidad y minimización del tratamiento, complementado por los principios generales de manejo ético de datos sensibles aplicables al proyecto.

Las fuentes incorporadas en `notebooks/` no exponen identificadores directos de las personas fallecidas (nombre, documento, contacto o equivalentes). En consecuencia, no fue necesario diseñar un proceso de anonimización primaria complejo; sí fue necesario aplicar controles de minimización, validación y agregación según la granularidad de cada fuente.

### Estrategia aplicada

La política documental del proyecto se resume en los siguientes principios:

1. **Conservar únicamente variables necesarias** para el análisis de mortalidad.
2. **Validar y normalizar** las variables sensibles o cuasi-identificadoras cuando la fuente fuese de mayor granularidad.
3. **Mantener el nivel de agregación original** cuando el proveedor ya publicara datos agregados.
4. **Reducir el riesgo de reidentificación** mediante supresión de columnas accesorias, generalización de edad y normalización de categorías atípicas.

### Justificación técnica

No fue necesario aplicar anonimización adicional sobre el material cargado porque las fuentes consultadas ya venían publicadas en formato anonimizado o agregado:

- **INE Guatemala**: microdatos sin identificadores directos; el notebook aplica supresión de columnas accesorias y generalización/validación de atributos sensibles.
- **MSPAS Guatemala**: tablas agregadas desde origen, sin nivel individual de registro.
- **IHME GBD 2023**: estimaciones agregadas por país, sexo, edad y causa.
- **Panamá INEC**: estadísticas ya agregadas por causa, sexo, edad, provincia y otras dimensiones.
- **WHO Mortality Database**: datos consolidados y agregados por país y causa.

Por tanto, el tratamiento ejecutado por el proyecto se limitó a **minimización de datos, normalización de esquemas, validación de dominios y control de calidad**, sin incorporar datos nominales ni identificadores directos en ninguna fase de Sandbox.

### Clasificación de sensibilidad

La sensibilidad se evalúa por el riesgo de re-identificación, no por la presencia de PII directa.

| Fuente | Sensibilidad | Justificación |
|--------|-------------|---------------|
| INE Guatemala | Media | No contiene identificadores directos; el riesgo residual proviene de cuasi-identificadores y se mitiga con supresión y generalización |
| MSPAS, IHME, Panamá INEC, WHO | Baja | Datos agregados en origen; no existe exposición individual |
| INEC Costa Rica | Media | PAD5 ya aplica supresión; riesgo residual bajo |
| RENAP | Alta (potencial) | Si se incorpora microdato, debe anonimizarse antes de ingesta |

### Técnicas aplicadas — INE Guatemala

**Supresión de columnas.** Se eliminan en la ingesta:

| Columna | Razón |
|---------|-------|
| `Puedif` (etnia) | Quasi-identificador de alto riesgo combinado con municipio pequeño |
| `Pnadif`, `Dnadif`, `Mnadif` (lugar de nacimiento) | Sin valor analítico para el proyecto |
| `Cerdef` (certificador) | Sin valor analítico |
| `Mredof` (municipio residencia duplicado) | Campo redundante |

**Generalización de edad.** Edades en meses → `0` años. Valores fuera de `[0, 120]` → `null`.

**Validación de causa.** Solo se conservan códigos CIE-10 con formato válido. Texto libre o códigos malformados → `null`, evitando que funcionen como identificador indirecto.

**Generalización de desconocidos.** `"Ignorado"` y vacíos → categorías genéricas (`"Desconocido"`, `"No Especificado"`), reduciendo la singularidad de registros.

**Riesgo residual.** El vector más probable es la combinación de municipio pequeño + causa rara + grupo etario + sexo. Para Fase 2 se aplicará supresión de celdas con menos de 5 registros en las tablas de análisis. Las visualizaciones BI mostrarán solo agregados por departamento, no por municipio.

### Correspondencia con notebooks

| Notebook | Fuente | Tratamiento relevante |
|----------|--------|-----------------------|
| `notebooks/gdrive_ine_guatemala_ingest.py` | INE Guatemala | Renombrado de campos, validación de CIE-10, supresión de columnas accesorias, normalización de valores desconocidos y generalización de edad |
| `notebooks/rds_mspas_guatemala_ingest.py` | MSPAS Guatemala | Lectura JDBC, normalización de nombres, estandarización de años y deduplicación |
| `notebooks/s3_ihme_gbd_ingest.py` | IHME GBD 2023 | Conversión de tipos, normalización semántica de categorías, exclusión de nulos y deduplicación |
| `notebooks/onedrive_panama_inec_ingest.py` | Panamá INEC | Normalización de columnas, validación de códigos CIE-10, estandarización de sexo/año y deduplicación |
| `notebooks/gdrive_sandbox_ingest.py` | Consolidación Sandbox | Reutilización de la misma política de normalización y control de calidad para aterrizaje en Sandbox |

### Principios EU Data Act aplicados

| Principio | Implementación |
|-----------|---------------|
| Portabilidad | Delta Lake con esquemas versionados, exportable en Parquet/CSV |
| Interoperabilidad | CIE-10, ISO 3166, grupos etarios WHO |
| Minimización de datos | Solo se ingesan columnas necesarias para el análisis |
| Transparencia | Este documento y el diccionario de datos cubren el linaje completo |

### Compromisos por fuente

| Fuente | Restricción | Compromiso |
|--------|------------|------------|
| IHME GBD 2023 | Licencia no comercial | Uso exclusivamente académico |
| WHO Mortality DB | CC BY-NC-SA 3.0 IGO | Atribución obligatoria en publicaciones |
| RENAP | Solicitud bajo Ley 57-2008 | Si se recibe microdato individual, anonimizar antes de ingesta |
| INEC Costa Rica | PAD5 uso público | No redistribuir archivos brutos |

---

## Decisiones de Limpieza

Registro de decisiones tomadas durante la ingesta (Raw → Sandbox).

### INE Guatemala — `sandbox.raw_ine`

**Valores nulos en columnas categóricas**

| Columna | Valor de relleno | Justificación |
|---------|-----------------|---------------|
| `escolaridad` | `"No Especificado"` | Coincide semánticamente con los valores existentes del campo |
| `sexo` | `"Desconocido"` | Campo no registrado en el acta |
| `estado_civil` | `"Desconocido"` | Campo no registrado |
| `nacionalidad` | `"Desconocido"` | Campo no registrado |
| `periodo_edad` | `"Desconocido"` | Rango etario no registrado |
| `dep_registro`, `mun_registro`, `mes_registro` | `"Desconocido"` | Lugar de registro no disponible |
| `dep_ocurrencia`, `mun_ocurrencia`, `area_geografica` | `"Desconocido"` | Lugar de ocurrencia no disponible |
| `lugar_defuncion`, `mes_ocurrencia` | `"Desconocido"` | No registrado |
| `dep_residencia`, `mun_residencia`, `lugar_residencia` | `"Desconocido"` | Frecuente en extranjeros o registros rurales incompletos |
| `asistencia_medica`, `tipo_ocurrencia` | `"Desconocido"` | No registrado |

**Columnas que se mantienen en `null`**

| Columna | Razón |
|---------|-------|
| `edad` | Numérico — `null` es la representación correcta de edad desconocida; imputar sesgaría distribuciones |
| `dia_ocurrencia` | Numérico — día no registrado |
| `anio_ocurrencia`, `anio_registro` | Numérico — año no registrado |
| `mes_ocurrencia_num` | Derivado de `mes_ocurrencia`; si el origen es nulo, el derivado también lo es |
| `causa_cie10` | `null` significa código ausente o inválido — semántica propia para análisis de causas |

**Otras transformaciones**

- `"Ignorado"` → `null` antes del relleno categórico.
- CIE-10: solo formato `^[A-Z][0-9]{2}[0-9A-Z]?$`; el resto → `null`.
- Edad en meses → `0`. Edades fuera de `[0, 120]` → `null`.
- Columnas eliminadas: `Puedif`, `Pnadif`, `Dnadif`, `Mnadif`, `Cerdef`, `Mredof`.
- `dropDuplicates()` al final.

### IHME GBD 2023 — `sandbox.raw_ihme`

- Columnas renombradas al español (ver [Pipelines](pipelines.md)).
- `Both/Male/Female → Ambos/Hombre/Mujer`; `Number/Rate/Percent → Número/Tasa/Porcentaje`.
- `valor` negativo → `null` (fila se conserva).
- `limite_superior`, `limite_inferior` pueden ser `null` si IHME no los reporta para cierta métrica.
- `dropna` sobre `pais`, `causa`, `anio`, `valor`.
- `dropDuplicates()`.

### MSPAS Guatemala — `sandbox.raw_mspas_*`

Tres tablas separadas porque tienen esquemas distintos; unirlas generaría nulls estructurales que no representan datos faltantes.

- Nombres de columnas normalizados a snake_case.
- `year → anio`.
- `"Ignorado"` en todas sus variantes → `null`.
- Años fuera de 2000–2030 → `null`.
- `dropDuplicates()`.

### Panamá INEC — `sandbox.raw_panama*`

- Nombres de columnas normalizados con `_norm_col` (Unicode, snake_case, prefijo `edad_` si empieza con dígito).
- `"-"`, `".."`, `"Ignorado"` → `null`.
- `causa_codigo` validado contra `^\d{3}(-\d{3})?$`.
- `sexo` solo acepta `"Total"`, `"Hombres"`, `"Mujeres"`.
- Años fuera de 2000–2030 → `null`.
- Columnas categóricas → `"Desconocido"`. Numéricas se mantienen en `null`.
- `dropDuplicates()`.

---

## Diccionario de Datos

### `sandbox.raw_ine`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `dep_registro` | String | Departamento de inscripción de la defunción |
| `mun_registro` | String | Municipio de inscripción |
| `mes_registro` | String | Mes de inscripción |
| `anio_registro` | String | Año de inscripción |
| `dep_ocurrencia` | String | Departamento donde ocurrió la muerte |
| `mun_ocurrencia` | String | Municipio de ocurrencia |
| `area_geografica` | String | Área urbana o rural |
| `sexo` | String | Sexo del fallecido |
| `dia_ocurrencia` | Integer | Día de ocurrencia (null si no registrado) |
| `mes_ocurrencia` | String | Mes de ocurrencia (nombre) |
| `mes_ocurrencia_num` | Integer | Mes de ocurrencia (1–12) |
| `anio_ocurrencia` | Integer | Año de ocurrencia |
| `edad` | Integer | Edad en años (0 si menor de un año; null si desconocida) |
| `periodo_edad` | String | Unidad de la edad (años, meses, días) |
| `estado_civil` | String | Estado civil |
| `escolaridad` | String | Nivel de escolaridad |
| `lugar_defuncion` | String | Tipo de lugar (hospital, domicilio, vía pública, etc.) |
| `nacionalidad` | String | Nacionalidad |
| `dep_residencia` | String | Departamento de residencia habitual |
| `mun_residencia` | String | Municipio de residencia habitual |
| `lugar_residencia` | String | Descripción del lugar de residencia |
| `causa_cie10` | String | Código CIE-10 de la causa básica de muerte |
| `asistencia_medica` | String | Tipo de asistencia recibida antes del fallecimiento |
| `tipo_ocurrencia` | String | Tipo de ocurrencia (natural, accidental, etc.) |
| `anio` | Integer | Año del archivo de origen (clave de partición) |

### `sandbox.raw_ihme`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `grupo_poblacion` | String | Grupo de población analizado |
| `medida` | String | Tipo de medida (Deaths, DALYs) |
| `pais` | String | País |
| `sexo` | String | Sexo (Hombre / Mujer / Ambos) |
| `grupo_edad` | String | Grupo etario |
| `causa` | String | Causa de muerte |
| `metrica` | String | Métrica (Número / Tasa / Porcentaje) |
| `anio` | Integer | Año |
| `valor` | Double | Valor estimado |
| `limite_superior` | Double | Intervalo de confianza superior |
| `limite_inferior` | Double | Intervalo de confianza inferior |

### `sandbox.raw_mspas_exceso`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `group` | String | Grupo de análisis |
| `observed_deaths` | Integer | Defunciones observadas |
| `expected_deaths` | Double | Defunciones esperadas según tendencia histórica |
| `excess_deaths` | Double | Defunciones en exceso |
| `excess_pct` | Double | Porcentaje de exceso |
| `anio` | Integer | Año |

### `sandbox.raw_panama`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `anio` | Integer | Año |
| `tabla` | String | Tipo de estadística de origen |
| `causa_codigo` | String | Código INEC de la causa (formato `\d{3}(-\d{3})?`) |
| `causa` | String | Descripción de la causa |
| `sexo` | String | Total / Hombres / Mujeres |
| `grupo_edad` | String | Grupo etario |
| `provincia` | String | Provincia de Panamá |
| `estado_civil` | String | Estado civil |
| `defunciones` | Integer | Número de defunciones |
| `fuente` | String | Nombre del archivo CSV de origen |

### Glosario

| Término | Definición |
|---------|-----------|
| CIE-10 | Clasificación Internacional de Enfermedades, décima revisión. Sistema estándar de codificación de causas de muerte. |
| Microdato | Registro a nivel individual: una fila = una defunción. |
| Sandbox | Capa de aterrizaje de datos crudos en Delta Lake. Preserva el dato sin transformaciones destructivas. |
| Stage | Capa de datos limpios y estandarizados (Fase 2). |
| Exceso de mortalidad | Diferencia entre defunciones observadas y las esperadas según tendencia histórica. Metodología para estimar el impacto real del COVID-19. |
| Período pre-COVID | 2015–2019 (antes del primer caso en Guatemala, marzo 2020). |
| Período post-COVID | 2020 en adelante. |
| SIGSA | Sistema de Información Gerencial de Salud (MSPAS). |
| RENAP | Registro Nacional de las Personas — fuente primaria de actas de defunción. |


### Notas

Nota de cobertura: el período objetivo del proyecto es 2015–2024. Algunas fuentes externas no publican todo el período; en particular, WHO Mortality Database para Guatemala no tenía datos disponibles para 2023 ni 2024 en la página consultada, por lo que su cobertura queda limitada a 2015–2022.