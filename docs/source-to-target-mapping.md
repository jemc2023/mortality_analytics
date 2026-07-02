# Source-To-Target Mapping - Excel

## Propósito

El **Source-To-Target Mapping** documenta cómo viaja cada dato relevante desde las fuentes aterrizadas en **Sandbox**, pasa por la capa **Stage** y termina en el modelo dimensional del **Data Warehouse**. Para este proyecto no se utiliza como un estándar rígido universal, sino como una matriz de trazabilidad que permite defender la Fase 2: qué tabla alimenta a cuál, qué campos se transforman y qué regla técnica se aplicó.

El archivo principal se encuentra aquí:

[Descargar Source-To-Target Mapping - Excel](source-to-target-mapping.xlsx)

[Visualizar en Google Sheets](https://docs.google.com/spreadsheets/d/1C-hy7eGUEAnScgwtlfXaTu_Jz8iJYTWa/edit?usp=sharing&ouid=112120769012459274077&rtpof=true&sd=true)

---

## Alcance del mapeo

El Excel cubre el flujo requerido por la Fase 2:

```text
Sandbox
  ↓ limpieza, tipado, homologación y validación
Stage
  ↓ conformado dimensional, llaves y hechos
Fact-Dimensiones / DW en la nube
  ↓ replicación y auditoría
DW local Greenplum
```

Las fuentes consideradas son:

| Fuente           | Capa Sandbox                  | Capa Stage      | Destino principal                                      |
| ---------------- | ----------------------------- | --------------- | ------------------------------------------------------ |
| INE Guatemala    | `sandbox.raw_ine`             | `stage.ine`     | `dm_mortality.fact_ine` y dimensiones compartidas      |
| MSPAS            | `sandbox.raw_mspas_*`         | `stage.mspas_*` | `dm_mortality.fact_mspas`                              |
| IHME GBD         | `sandbox.raw_ihme`            | `stage.ihme`    | `dm_mortality.fact_ihme`                               |
| Panamá INEC      | `sandbox.raw_panama`          | `stage.panama`  | `dm_mortality.fact_panama`                             |
| WHO Mortality DB | `sandbox.raw_who_mortality_*` | `stage.who_*`   | `dm_mortality.fact_who_deaths` y `fact_who_population` |

---

## Estructura del Excel

El archivo contiene cuatro hojas enfocadas en el movimiento del dato:

| Hoja                   | Contenido                                                                     |
| ---------------------- | ----------------------------------------------------------------------------- |
| `Resumen`              | Propósito, alcance y forma de lectura del documento.                          |
| `Sandbox_to_Stage`     | Mapeo desde tablas crudas de Sandbox hacia tablas limpias y tipadas de Stage. |
| `Stage_to_DW`          | Mapeo desde Stage hacia dimensiones y tablas de hechos del Data Warehouse.    |
| `Interoperabilidad_DW` | Evidencia esperada para la relación Databricks cloud → Greenplum local.       |

Las hojas de mapeo usan encabezados agrupados para que la lectura sea similar a una matriz Source/Target:

- **Origen**: `fuente`, `capa_origen`, `tabla_origen`, `campo_origen`.
- **Destino**: `capa_destino`, `tabla_destino`, `campo_destino`, `tipo_dato_destino`.
- **Transformación / Validación**: `tipo_movimiento`, `transformacion_aplicada`, `manejo_nulos`, `calidad_validacion`, `observaciones`.

Con esto se evita separar reglas o modelo dimensional en hojas adicionales: la explicación queda en la misma fila donde ocurre el movimiento del dato.

---

## Ejemplo de lectura

Una fila del mapping se interpreta así:

| `mapping_id` | Tabla origen      | Campo origen | Tabla destino | Campo destino              | Tipo de movimiento     | Transformación                                  |
| ------------ | ----------------- | ------------ | ------------- | -------------------------- | ---------------------- | ----------------------------------------------- |
| `S2S-003`    | `sandbox.raw_ine` | `Caudef`     | `stage.ine`   | `causa_cie10 / cie10_code` | `normalizado_validado` | Trim, uppercase y validación de formato CIE-10. |

Esto significa que el campo original de causa de muerte del INE se limpia y valida antes de formar parte de la tabla Stage. Posteriormente ese valor se usa para alimentar `dm_mortality.dim_causa` y las tablas de hechos que dependen de la causa de muerte.

---

## Tipos de movimiento documentados

La columna `tipo_movimiento` resume qué ocurrió con el campo o conjunto de campos durante el paso de una capa a otra:

| Tipo                   | Significado                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------ |
| `renombrado`           | El campo cambia de nombre para quedar claro y consistente.                           |
| `tipado`               | El valor se convierte a un tipo analítico, por ejemplo `NUMBER`, `DATE` o `VARCHAR`. |
| `normalizado`          | Se homologan textos, categorías o formatos.                                          |
| `normalizado_validado` | Además de normalizar, se valida contra un dominio o patrón, como CIE-10.             |
| `derivado`             | El campo destino se calcula desde uno o más campos origen.                           |
| `unpivot_normalizado`  | Una tabla ancha se convierte a formato largo.                                        |
| `join_lookup`          | El valor se conecta con una dimensión o catálogo para obtener llaves.                |
| `agregado_lookup`      | Se cargan métricas o hechos usando llaves dimensionales.                             |
| `replicado`            | El dato pasa del DW cloud al DW local conservando estructura.                        |
| `auditoria`            | Se registra evidencia de ejecución o consistencia del proceso.                       |

---

## Cómo defenderlo en la presentación

Durante la defensa, este documento debe explicarse como evidencia de trazabilidad:

1. **Sandbox** conserva el aterrizaje desde fuentes heterogéneas.
2. **Stage** aplica reglas de limpieza, tipado y estandarización.
3. **Fact-Dimensiones** organiza los datos para análisis con esquema estrella.
4. **DW cloud y DW local** demuestran interoperabilidad mediante replicación, auditoría y extracción cruzada.

La idea central es demostrar que cada campo del Data Warehouse no aparece “mágicamente”: tiene una fuente, una transformación documentada y una razón analítica dentro del proyecto de mortalidad.
