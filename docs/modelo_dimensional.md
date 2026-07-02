# Modelo dimensional (cubo OLAP) — decisiones y observaciones

Documento de diseño del cubo de mortalidad. Recoge el análisis de la raw data y
de la capa de staging, las decisiones de alcance tomadas y los problemas de
conformidad que quedan por resolver. Es la referencia para construir las
dimensiones y los hechos.

> **Alcance temporal del proyecto:** 2015–2022, con enfoque **pre-COVID vs.
> post-COVID**. Marco: Pre-COVID = 2015–2019; COVID/Post = 2020–2022.

---

## 1. Cobertura real por fuente (verificado contra la raw data)

| Fuente (hecho) | Rango real | Pre-COVID (15–19) | COVID/Post (20–22) | ¿Sirve pre/post? |
|---|---|:---:|:---:|---|
| INE (`FACT_INE`) | 2015–2024 | ✅ | ✅ | **Sí, completo** |
| Panamá (`FACT_PANAMA`) | 2015–2024 | ✅ | ✅ | **Sí, completo** |
| IHME (`FACT_IHME`) | 2015–2023 | ✅ | ✅ | **Sí, completo** |
| MSPAS general (`FACT_MSPAS`.defunciones) | 2010–2024 | ✅ | ✅ | **Sí, completo** |
| MSPAS tasa (`FACT_MSPAS`.tasa_por_100k) | 2001–**2019** | ✅ | ❌ | **Solo pre-COVID** |
| WHO deaths (`WHO_DEATHS`) | **2000–2003** | ❌ | ❌ | **No (fuera de rango)** |
| MSPAS exceso (`FACT_MSPAS_EXCESO`) | **solo 2022** | ❌ | parcial | **No relevante** |

**Núcleo sólido para pre/post-COVID:** INE (Guatemala, detalle), IHME (regional
CA) y MSPAS general (totales GTM). Las tres cubren 2015–2022 completo.

---

## 2. Decisiones de alcance (hechos)

### 2.1 Se ELIMINA `FACT_MSPAS_EXCESO` (definitivo)
- Solo existe 2022 → no aporta a la comparación pre/post-COVID.
- Además modelaba mal la dimensión `grupo`: eran cortes marginales solapados
  (`Total`, `<65`, `>65`, `Hombres`, `Mujeres`) que combinaban dos particiones
  independientes (edad y sexo) en una sola columna de texto, sin ser un cruce
  real. No encajaban en `DIM_GENERO`/`DIM_ETARIO` sin riesgo de doble conteo.
- No se conserva ni como hecho a nivel nacional.

### 2.2 `WHO_DEATHS` — MANTENER (corrección 2026-06-18)
- La raw data de WHO cubre **2015–2022** completo (1,344 filas de deaths +
  672 de population, 8 años), **dentro** de la ventana pre/post-COVID. La
  sección previa ("candidato a ELIMINAR, solo 2000–2003") estaba equivocada:
  correspondía a un export obsoleto; el actual sí trae años recientes.
- `FACT_WHO_POPULATION` también cubre 2015–2022 → sirve como denominador.
- **Observación de conformidad (§6.1, corrección 2026-06-18):** WHO Mortality
  usa su propia lista de `CGXXXX` (Nivel 1: Communicable / Noncommunicable /
  Injuries / Ill-defined), **no** las 16 causas GBD Nivel 2 de IHME. Los CG de
  WHO no coinciden con los del diccionario GBD (p. ej. WHO `CG0590` =
  "Noncommunicable diseases", pero en el diccionario `CG0590` =
  "Neurological disorders"). Por eso `gbd_code` queda NULL en WHO y
  `gbd_nombre` se puebla con `indicator_name` (best-effort, §6.4, misma regla
  que INE/Panamá para causas fuera de las 16). WHO **no** se une por igualdad
  directa de `gbd_code` con las demás fuentes.

### 2.3 `FACT_MSPAS` — observación de cobertura
- `defunciones` (mortalidad general) cubre 2015–2022 completo.
- `tasa_por_100k` **acaba en 2019** → quedará NULL para 2020–2022. En dashboards
  pre/post, la tasa MSPAS solo tendrá lado pre-COVID. **Documentar.**

### 2.4 `FACT_IHME` — crítico RESUELTO
- `valor` significa cosas distintas según `medida` (Deaths/DALYs/YLLs/…) ×
  `metrica` (Número/Tasa/Porcentaje). Sin esas columnas se sumarían
  muertes + DALYs + tasas + % en una sola columna.
- **Solución aplicada:** se añadieron `DIM_MEDIDA` y `DIM_METRICA`, y `FACT_IHME`
  ahora tiene `id_medida` + `id_metrica`.
- **Regla BI:** filtrar siempre `medida` + `metrica` antes de cualquier
  `SUM(valor)`. `metrica='Número'` es aditivo; `Tasa`/`Porcentaje` NO.

### 2.5 `FACT_PANAMA` — alcance reducido
Solo se usan: `grupo_edad`, `sexo`, `causa`, `país`, `año`, `defunciones`,
`source`, `record_hash`, `ingestion_ts`. Se descartan las sub-tablas de
provincia, certificación, estado conyugal, actividad económica y tasa.
- La data local solo trae la sub-tabla `causa_edad_sexo` (las demás no están en
  los CSV locales). Coincide con el alcance elegido.
- **Reglas de carga obligatorias:** ver sección 4 (Panamá tiene subtotales en los
  tres ejes y duplica si se suma sin filtrar).

---

## 3. Dimensiones — problemas y soluciones

### 3.1 `DIM_TIEMPO` / `DIM_GEOGRAFIA` — SIMPLIFICADAS ✅
- **Decisión:** quedarse **solo con ocurrencia**. Se eliminan los roles de
  registro y residencia. Esto resuelve el problema de "roles aplastados"
  (varios roles en una misma fila) que explotaba filas y confundía el grano.
- `semana_epidemiologica` se elimina (no existe en ninguna fuente real).
- `DIM_TIEMPO`: grano = **año** (la mayoría de fuentes son anuales); mes/día solo
  poblados desde INE.

### 3.2 `DIM_SOURCE` — mal modelada, PENDIENTE
- Tiene `ingestion_ts` y `record_hash`: son **linaje por fila**, únicos por
  registro. Al estar en una dimensión **conformada** (compartida por todos los
  hechos), la vuelven 1:1 con los hechos → deja de ser dimensión.
- **Solución:**
  - `DIM_SOURCE`/`DIM_FUENTE` = catálogo de sistemas (INE/WHO/IHME/MSPAS/Panamá),
    pocas filas, atributos descriptivos (cobertura, granularidad, tipo de datos).
  - `ingestion_ts` y `record_hash` → **columnas de auditoría en cada hecho**
    (degeneradas), no en la dimensión.
  - `record_hash` nunca debe ser dimensión (único por fila por definición).

### 3.3 `DIM_CAUSA` — normalización a GBD, PLAN DEFINIDO (sección 6)
Hay **cuatro vocabularios de causa distintos**, uno por fuente. La solución es
normalizar **todas** a un código GBD común. Ver sección 6 para el detalle.

Columnas objetivo de `DIM_CAUSA`: `cie-10_code`, `cie-10_nombre`, `GBD_code`,
`GBD_nombre`. El bloque CIE-10 es **best-effort / omitible** si su poblado resulta
muy complejo; el bloque GBD es **obligatorio** (es la llave conformada).

### 3.4 `DIM_ETARIO` — conformidad, SOLUCIÓN DEFINIDA (sección 5)
Este es el punto más importante pendiente. Ver sección 5.

---

## 4. Reglas de carga de Panamá (anti doble-conteo)

`causa_edad_sexo` tiene **subtotales en los tres ejes**; todos duplican si se
suman sin filtrar. Verificado contra la raw data (32.525 filas, 2015–2024):

| Eje | Hallazgo (verificado) | Regla de carga |
|---|---|---|
| **Sexo** | `Total` = `Hombres` + `Mujeres` (causa 003, 2022: Total=125=H+M) | Cargar **solo `Hombres` + `Mujeres`**, excluir `Total` |
| **Causa** | Códigos-rango (`001-025`, `064-071`) son agregados de los simples; coexisten en la misma celda (`064-071`=737 = Σ`065..071`, verificado 2024) | **Implementado:** `stage.panama` trae columna `nivel` (`grupo`/`simple`) y conserva ambos (≈411k def solo existen como grupo, p.ej. externas `095`). Al sumar se filtra **un solo `nivel`**. ⚠️ los simples NO cubren todo (`066` hipertensivas, `071` resto → sin GBD) |
| **Edad** | Bandas solapadas e inconsistentes entre años (2015 trae años simples + `Menores de 5`; 2016–19 `1 a 4`; 2020–24 años simples) | Normalizar (ver 5.2): colapsar `1,2,3,4`→`1 a 4`, **descartar** `Menores de 5` |

---

## 5. `DIM_ETARIO` — esquema común + crosswalk

### 5.1 Quién aporta edad realmente

| Fuente | Edad que trae | Acción |
|---|---|---|
| INE | año simple `0…120` | bucketizar a banda |
| Panamá | bandas (con solapes) | mapear + limpiar |
| WHO_POPULATION | quinquenios `0,1-4,5-9…85+` | mapeo casi directo |
| **IHME** | **solo `All ages`** | → miembro único `ALL` |

La conformidad real es **INE ↔ Panamá ↔ WHO_pop**, y los tres caben en el
estándar quinquenal GBD/WHO. IHME solo necesita el miembro "Todas las edades".

### 5.2 Grid canónico (filas de la dimensión)

| id_etario | grupo_edad_codigo | grupo_edad_nombre | edad_min | edad_max | categoria_etaria |
|---|---|---|---|---|---|
| 1 | `LT1` | Menores de 1 | 0 | 0 | Niñez |
| 2 | `01-04` | 1 a 4 | 1 | 4 | Niñez |
| 3 | `05-09` | 5 a 9 | 5 | 9 | Niñez |
| 4 | `10-14` | 10 a 14 | 10 | 14 | Niñez |
| 5 | `15-19` | 15 a 19 | 15 | 19 | Juventud |
| 6 | `20-24` | 20 a 24 | 20 | 24 | Juventud |
| 7 | `25-29` | 25 a 29 | 25 | 29 | Juventud |
| 8 | `30-34` | 30 a 34 | 30 | 34 | Adultez |
| 9 | `35-39` | 35 a 39 | 35 | 39 | Adultez |
| 10 | `40-44` | 40 a 44 | 40 | 44 | Adultez |
| 11 | `45-49` | 45 a 49 | 45 | 49 | Adultez |
| 12 | `50-54` | 50 a 54 | 50 | 54 | Adultez |
| 13 | `55-59` | 55 a 59 | 55 | 59 | Adultez |
| 14 | `60-64` | 60 a 64 | 60 | 64 | Adultez |
| 15 | `65-69` | 65 a 69 | 65 | 69 | Vejez |
| 16 | `70-74` | 70 a 74 | 70 | 74 | Vejez |
| 17 | `75-79` | 75 a 79 | 75 | 79 | Vejez |
| 18 | `80-84` | 80 a 84 | 80 | 84 | Vejez |
| 19 | `85+` | 85 y más | 85 | *(null)* | Vejez |
| 98 | `UNK` | No especificada | *(null)* | *(null)* | No especificado |
| 99 | `ALL` | Todas las edades | 0 | *(null)* | Total |

`edad_max` es null en `85+` y `ALL`. `categoria_etaria` habilita el roll-up
Niñez / Juventud / Adultez / Vejez.

### 5.3 Crosswalk (cómo cada fuente llena `id_etario`)

```
INE (año simple):    id_etario = banda donde edad_min <= edad <= edad_max
                     (edad=0 -> LT1; edad 1..4 -> 01-04; … >=85 -> 85+)

Panamá (etiquetas):  'Menores de 1'        -> LT1
                     '1','2','3','4'       -> 01-04   (colapsa años simples)
                     '1 a 4'               -> 01-04
                     '5 a 9'               -> 05-09 … '85 y más' -> 85+
                     'No especificada'     -> UNK
                     'Menores de 5'        -> ❌ DESCARTAR (solapa LT1+01-04)

WHO_POP (códigos):   age00 -> LT1, age01_04 -> 01-04, … age85_over -> 85+
                     age55_74, age75_over  -> ❌ DESCARTAR (agregados solapados)

IHME:                'All ages'            -> ALL
```

### 5.4 Reglas anti doble-conteo (críticas)

1. **Descartar bandas agregadas que solapan a las hoja:** `Menores de 5`
   (Panamá 2015) y `age55_74` / `age75_over` (WHO).
2. **Colapsar los años simples 1–4 de Panamá** a `01-04`, igualándolos con los
   años que traen `'1 a 4'`. Así la banda 1–4 significa lo mismo en los 10 años.

### 5.5 Resultado
- Una `id_etario` significa la misma banda en `FACT_INE`, `FACT_PANAMA` y
  `FACT_WHO_POPULATION` → comparables entre sí.
- `FACT_IHME` cuelga del miembro `ALL` (coherente: no tiene desglose por edad).
- Roll-up por `categoria_etaria` uniforme entre países.
- **Decisión abierta:** mantener `LT1` y `01-04` separados (recomendado, porque
  Panamá y WHO distinguen `<1`) o fusionarlos en `00-04`. Siempre se puede
  agregar hacia arriba, nunca al revés.

---

## 6. Normalización de causa a GBD (conformar `DIM_CAUSA`)

**Objetivo:** que `FACT_INE`, `FACT_PANAMA`, `FACT_IHME` y `WHO_DEATHS` compartan
un **código GBD común** (`GBD_code` + `GBD_nombre`), para poder comparar causas
entre fuentes/países. La normalización se hace en la **capa stage** (cada tabla
sale de stage ya con sus columnas de causa normalizadas).

> **Orden de trabajo: el primer mapeo a consolidar es Panamá.**

### 6.0 Archivos de referencia

| Archivo | Qué es | Uso |
|---|---|---|
| `Deaths.XLSX` | GBD Appendix Table 6: nombres de causa GBD ↔ rangos **ICD-10/ICD-9** (jerárquica, 306 filas) | Crosswalk maestro **CIE-10 → GBD** |
| `Decodificador panama.pdf` | Boletín INEC Panamá (Estadísticas Vitales Vol. III). Trae la **Lista abreviada de 103 grupos** con `código → causa → rango CIE-10` ("Lista detallada", p. ej. `001-025 → A00-B99`) | Decodificar `causa_codigo` de Panamá a CIE-10 |
| `mapeo_completo_gbd` (dict, abajo) | 16 causas GBD **Nivel 2** → `who_code` (CGXXXX) + `cause_id` | Mapeo directo de nombres GBD y unificación del código |

### 6.1 Nivel de conformidad: **GBD Nivel 2 (16 causas)**

IHME en esta data viene exactamente con las **16 causas GBD de Nivel 2**
(Neoplasms, Cardiovascular diseases, …). Ese es el nivel al que se conforman
todas las fuentes. INE y Panamá tienen CIE-10 mucho más fino → se mapea cada
código CIE-10 a su **padre GBD Nivel 2**. (El detalle CIE-10 fino se conserva en
`cie-10_code`/`cie-10_nombre` para INE, que es quien lo tiene real.)

**Llave común = `GBD_code` (CGXXXX) + `GBD_nombre`.**

> **Corrección 2026-06-18 (WHO):** la sección anterior decía que WHO usa los
> `CGXXXX` de forma nativa y son los mismos `who_code` del diccionario → unión
> por igualdad directa. **Esto es FALSO para la data real.** WHO Mortality
> trae 4 categorías de Nivel 1 (`CG0010` Communicable, `CG0590`
> Noncommunicable, `CG1480` Injuries, `CG1610` Ill-defined), no las 16 de
> Nivel 2. Además los CG de WHO no coinciden con los del diccionario (WHO
> `CG0590` = "Noncommunicable diseases" vs diccionario `CG0590` =
> "Neurological disorders"). Por eso en WHO `gbd_code` queda NULL y
> `gbd_nombre` se puebla con `indicator_name` (best-effort, §6.4). La
> conformidad real de `gbd_code` es **INE ↔ Panamá ↔ IHME**; WHO cuelga
> separadamente con su `gbd_nombre` descriptivo.

### 6.2 Diccionario maestro GBD Nivel 2 (16 causas)

```python
mapeo_completo_gbd = {
    "Neoplasms":                                     {"who_code": "CG0600", "cause_id": 410},
    "Cardiovascular diseases":                       {"who_code": "CG0530", "cause_id": 491},
    "Neglected tropical diseases and malaria":       {"who_code": "CG0250", "cause_id": 344},
    "Nutritional deficiencies":                      {"who_code": "CG0470", "cause_id": 386},
    "Diabetes and kidney diseases":                  {"who_code": "CG0510", "cause_id": 955},
    "Mental disorders":                              {"who_code": "CG0610", "cause_id": 545},
    "Neurological disorders":                        {"who_code": "CG0590", "cause_id": 542},
    "Self-harm and interpersonal violence":          {"who_code": "CG0860", "cause_id": 717},
    "COVID-19":                                      {"who_code": "CG0995", "cause_id": 1013},
    "Transport injuries":                            {"who_code": "CG0810", "cause_id": 688},
    "Digestive diseases":                            {"who_code": "CG0580", "cause_id": 526},
    "Unintentional injuries":                        {"who_code": "CG0850", "cause_id": 696},
    "Diarrheal diseases":                            {"who_code": "CG0350", "cause_id": 302},
    "HIV/AIDS and sexually transmitted infections":  {"who_code": "CG0290", "cause_id": 366},
    "Respiratory infections and tuberculosis":       {"who_code": "CG0390", "cause_id": 337},
    "Chronic respiratory diseases":                  {"who_code": "CG0570", "cause_id": 508},
}
```

PySpark (mapa plano para derivar la columna):

```python
from pyspark.sql.functions import create_map, lit
from itertools import chain
mapeo_cg = {k: v["who_code"] for k, v in mapeo_completo_gbd.items()}
map_expr = create_map([lit(x) for x in chain(*mapeo_cg.items())])
df = df.withColumn("GBD_code", map_expr[df["causa"]])
```

### 6.3 Pipeline por fuente (todo en stage)

| Fuente | Código origen | Cómo llega a GBD | CIE-10 |
|---|---|---|---|
| **IHME** | `causa` (nombre GBD, ej. `Neoplasms`) | Directo vía `mapeo_completo_gbd` → `GBD_code`(CGXXXX) + `cause_id` + `GBD_nombre` | — (no aplica) |
| **WHO_DEATHS** | `indicator_code` (`CGXXXX`) + `icd10_group` | `indicator_code` **ya es** `GBD_code`; normalizar `icd10_group` y validar contra el diccionario | desde `icd10_group` |
| **INE** | `causa_cie10` (`A09`, `J18`…) | CIE-10 → padre GBD Nivel 2 vía `Deaths.XLSX` (rangos ICD-10) → `GBD_code`+`GBD_nombre` | `cie-10_code` nativo + `cie-10_nombre` |
| **Panamá** | `causa_codigo` (lista 103, `001-025`) | lista 103 → rango CIE-10 (PDF) → padre GBD Nivel 2 (`Deaths.XLSX`) → `GBD_code`+`GBD_nombre` | rango CIE-10 desde PDF |

**Salida estándar (todas las tablas con causa):** columnas `cie-10_code`,
`cie-10_nombre`, `GBD_code`, `GBD_nombre`. `cie-10_*` puede quedar null donde la
fuente no lo provee (IHME) o si su poblado es muy costoso (omitible).

### 6.4 Tareas pendientes de implementación

> **Estado:** §6 implementado en stage (tareas 1–4). Las 4 fuentes salen con
> columnas `cie10_code`, `cie10_nombre`, `gbd_code`, `gbd_nombre`, `gbd_cause_id`
> (snake_case, sin guion, para evitar el escape de `cie-10_*` en Spark/Delta).
> El crosswalk se genera con `scripts/transformation/build_gbd_crosswalk.py`
> (`data/processed/cie10_gbd_nivel2.csv`, `panama_lista103_gbd.csv`) y se **embebe**
> en los notebooks (sin I/O en runtime). Regla aplicada: COVID (U07) se fuerza a
> `CG0995`; todo código ambiguo, agregado o fuera de las 16 → `gbd_code = NULL`.

1. ✅ **Panamá:** lista 103 → CIE-10 (PDF) → GBD Nivel 2 (`Deaths.XLSX`). `staging/panama.py`.
   Dos niveles de mapeo (ver dict `PANAMA_LISTA103`):
   - **16 causas de IHME** (llave conformada completa): `gbd_code` + `gbd_nombre` + `gbd_cause_id`.
     Incluye reasignar los "resto de capítulo" a su capítulo cuando colapsa a una sola
     (071 circulatorio→Cardiovascular, 061 nervioso→Neurological, 057 mental→Mental,
     085 renal→Diabetes and kidney), igual que ya se hacía con 066 hipertensivas.
   - **Causas GBD Nivel 2 FUERA de las 16** (decisión 2026-06-18, reduce nulos): se puebla
     **solo `gbd_nombre`** (autoritativo, verificado vs rangos ICD-10 de WHO Mortality);
     `gbd_code`/`gbd_cause_id` quedan **NULL** porque el `CGxxxx` no existe en ninguna
     fuente confiable y no se fabrica. Cubre: piel 082, osteomuscular 083, órganos de los
     sentidos 062/063, perinatal 092, congénitas 093, uso de sustancias 056, otras
     infecciosas 008/010/011/012/059.
   - **NULL total** (sin nombre): agregados multi-causa (095 externas, sin simples en la
     data), códigos especiales/COVID (U00-12, U00-U85), mal definidos (094 R00-R99) y
     residuales realmente mixtos (086, 077, 054, 049, 050, 025).
2. ✅ **IHME:** `mapeo_completo_gbd` sobre `causa` → `gbd_code`/`gbd_nombre`/
   `gbd_cause_id`. cie10 no aplica (NULL). `staging/ihme.py`.
3. ✅ **INE:** lookup CIE-10 (3 chars) → GBD Nivel 2 desde los rangos de `Deaths.XLSX`
   (811 códigos, broadcast join); `cie10_code` = `causa_cie10`. `staging/ine.py`.
4. ✅ **WHO_DEATHS:** `indicator_code` (CGXXXX) usado como `gbd_code`; validado
   contra las 16; nombre/cause_id derivados. `staging/who_mortality.py`.
5. ⏳ **`DIM_CAUSA`:** poblar desde la unión de las 4 fuentes ya normalizadas
   (deduplicado por `gbd_code`). — capa dimensión, pendiente.

> **Brecha conocida (revisar):** la neumonía no especificada (`J17`, `J18`) y otros
> 15 códigos de 3 chars que GBD reasigna a nivel decimal quedan en `gbd_code = NULL`
> en INE. Panamá no puede aislar COVID (su bucket `U00-U85` es demasiado amplio).

> **Riesgo a vigilar:** valores fuera de las 16 causas (subtotales tipo "All
> Causes" `CG0000`, o causas no mapeadas) → deben quedar como `GBD_code = NULL`
> y revisarse, nunca forzarse a una categoría.

---

## 7. Estado de decisiones

| # | Tema | Estado |
|---|---|---|
| 1 | Eliminar `FACT_MSPAS_EXCESO` | ✅ Decidido (definitivo) |
| 2 | IHME `medida`/`metrica` (DIM_MEDIDA, DIM_METRICA) | ✅ Aplicado |
| 3 | `FACT_PANAMA` alcance reducido (edad/sexo/causa/país/año) | ✅ Decidido |
| 4 | `DIM_TIEMPO`/`DIM_GEOGRAFIA` solo ocurrencia | ✅ Decidido |
| 5 | `DIM_ETARIO` grid canónico + crosswalk | ✅ Implementado en stage (INE, Panamá, IHME, WHO) |
| 6 | Reglas anti doble-conteo Panamá | ✅ Implementado vía columna `nivel` (grupo/simple) en `stage.panama` |
| 7 | `WHO_DEATHS` — mantener (cubre 2015–2022) | ✅ Decidido (corrección 2026-06-18, antes era "eliminar") |
| 8 | `DIM_SOURCE` → catálogo + auditoría en hecho | ⏳ Pendiente |
| 9 | Normalización de causa a GBD en stage (sección 6, tareas 1–4) | ✅ Implementado (INE, Panamá, IHME, WHO) |
| 10 | `DIM_CAUSA` poblada desde las 4 fuentes normalizadas (sección 6, tarea 5) | ⏳ Pendiente (capa dimensión) |
