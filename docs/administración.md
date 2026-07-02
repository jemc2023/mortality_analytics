# Gestión y Administración del Proyecto

> **Cliente:** PNUD · Ministerio de Salud Pública y Asistencia Social (MSPAS)  
> **Firma Consultora:** DataMortality Analytics Group  
> **Duración:** 4 meses (marzo — junio 2026)  
> **Metodología:** Ágil Scrum — 3 Sprints + Cierre

---

## 1. Project Charter

El **Project Charter** formaliza el inicio del proyecto, estableciendo el alcance, objetivos, stakeholders, hitos, presupuesto, supuestos, restricciones y criterios de éxito. Este documento fue elaborado siguiendo el estándar PMI y constituye el acta de constitución oficial de la consultoría ante el PNUD y el MSPAS.

El documento completo incluye 24 campos distribuidos en tres partes:

- **Parte I — Información General:** Título, alcance, PM, sponsors, entregables, objetivos, recursos, stakeholders, hitos, presupuesto, supuestos, restricciones y riesgos de alto nivel.
- **Parte II — Información del Negocio:** Términos contractuales, caso de negocio, expectativas y requisitos de stakeholders, criterios de éxito.
- **Parte III — Información Organizacional:** Plan de mejora de procesos, definición de procesos, lecciones aprendidas, herramientas y plantillas.

> **Ver archivo completo:** [Project_Charter.docx](https://docs.google.com/document/d/1ec7Ev_cSdQ4dw1ul6KRx7rWRXFlhNiLtspwN4ja8y6g/edit?usp=sharing)

### Resumen Ejecutivo del Project Charter

| Campo | Valor |
|-------|-------|
| **Project Title** | Plataforma Analítica de Mortalidad End-to-End: Análisis Pre-COVID y Post-COVID en Guatemala y Centroamérica |
| **Project Manager** | Sebastián Valle — Tutor Académico / PM |
| **Sponsors** | PNUD / MSPAS de Guatemala |
| **Presupuesto** | USD $187,400 (suma alzada, todo incluido) |
| **Duración** | 4 meses (marzo — junio 2026) |
| **Hitos principales** | Hito 0 (anticipo) → Hito 1 (Sandbox) → Hito 2 (DW) → Hito 3 (ML+BI) → Hito 4 (Cierre) |
| **Metodología** | Ágil Scrum — 3 Sprints + Cierre |

---

## 2. Diagrama de Gantt (4 Meses)

El cronograma del proyecto abarca **17 semanas** distribuidas en 4 meses calendario (marzo — junio 2026). Se organiza en tres Sprints correspondientes a las fases del proyecto, más un período de cierre:

| Sprint | Período | Semanas | Fase | Entregable Principal |
|--------|---------|---------|------|---------------------|
| **Sprint 1** | Marzo 2026 | 1 – 4 | Fase 1 — Ingesta y Sandbox | Datos crudos consolidados en Sandbox, diccionario de datos, arquitectura de despliegue |
| **Sprint 2** | Abril 2026 | 5 – 8 | Fase 2 — Transformación y DW | Pipeline ELT completo, DW nube + DW local interoperables |
| **Sprint 3** | Mayo – Junio 2026 | 9 – 16 | Fase 3 — ML, BI y Cierre | 4 modelos ML, 4 dashboards BI, informe final, gestión de proyecto |
| **Cierre** | Junio 2026 | 17 | Cierre | Documentación final, transferencia de conocimiento |

El diagrama de Gantt detalla 31 tareas organizadas jerárquicamente con su WBS, fechas de inicio y fin, duración en días, y barras visuales por semana. Incluye 4 hitos marcados con rombos rojos.

> **Ver archivo completo:** [Gantt_4Meses.xlsx](https://docs.google.com/spreadsheets/d/1R6__zXzHIDvA_g1BOl6mSTuCtCHQ_Ma7/edit?usp=sharing&ouid=100455211682358519319&rtpof=true&sd=true)

---

## 3. Estructura de Desglose de Trabajo (EDT / WBS)

La EDT descompone el alcance total del proyecto en paquetes de trabajo jerárquicos, identificados con códigos WBS. Cada paquete representa un entregable verificable.

### 3.1 Fase 1 — Ingesta y Fundamentos de Datos (Sprint 1)

| WBS | Entregable | Detalle |
|-----|-----------|---------|
| **1** | **Repositorio de Datos de Mortalidad** | |
| 1.1 | Set de datos INE | Obtención, validación y carga de microdatos de defunciones CIE-10 |
| 1.2 | Set de datos RENAP | Solicitud formal (Ley 57-2008), seguimiento y documentación del oficio |
| 1.3 | Set de datos OMS (WHO) | Descarga de WHO Mortality Database y WHO Population |
| 1.4 | Set de datos MSPAS | Obtención de estadísticas vitales y exceso de mortalidad |
| 1.5 | Set de datos Centroamérica | Datos de IHME GBD 2023, Panamá INEC, Costa Rica INEC |
| **2** | **Infraestructura de Orígenes de Datos** | |
| 2.1 | Google Drive | Configuración de API y service account para acceso a `semis2_raw_data/ine/` |
| 2.2 | SharePoint / OneDrive | App registration Azure AD para acceso a datos de Panamá |
| 2.3 | Base de datos AWS RDS | Instancia PostgreSQL con esquema `raw_data` para fuente MSPAS |
| 2.4 | Bucket AWS S3 | Configuración de bucket `mortality-analytics-semi2/raw/` para objetos |
| 2.5 | Servidor web local (Nginx) | Configuración de Nginx + DevTunnel para exponer archivos WHO |
| **3** | **Pipeline de Datos (ETL)** | |
| 3.1 | Extracción de datos | Conectores a 5+ fuentes (GDrive API, MS Graph, boto3/S3, JDBC/RDS, HTTP/Nginx) |
| 3.2 | Transformación de datos | Políticas de limpieza, normalización CIE-10, validación, deduplicación |
| 3.3 | Carga de datos | Creación de esquema y tablas Sandbox en Databricks Delta Lake |
| **4** | **Documentación** | |
| 4.1 | Decisiones arquitectónicas | Documentación de selección de herramientas, arquitectura y justificaciones |
| 4.2 | Diagramas de arquitectura | Draw.io: 4 vistas (Solución, Despliegue, Sandbox, Stage) |
| 4.3 | Políticas de transformación | Registro de reglas de limpieza, normalización y control de calidad |
| 4.4 | Diccionario y linaje de datos | Catálogo de metadatos, data lineage fuente → Sandbox |

### 3.2 Fase 2 — Transformación y Data Warehouse (Sprint 2)

| WBS | Entregable | Detalle |
|-----|-----------|---------|
| **5** | **Arquitectura por Capas** | |
| 5.1 | Revisión capa Sandbox | Auditoría de datos crudos provenientes de Fase 1 |
| 5.2 | Definición capa Stage | Esquema de tablas limpias, tipadas y estandarizadas |
| 5.3 | Definición capa Fact-Dimensions | Modelo dimensional estrella (5 hechos + 5 dimensiones) |
| 5.4 | Diseño del flujo | Sandbox → Stage → Fact-Dimensions |
| **6** | **Transformación de Datos** | |
| 6.1 | Reglas de transformación | Definición de reglas de negocio y calidad |
| 6.2 | Limpieza y estandarización | Normalización de catálogos, CIE-10 → GBD crosswalk |
| 6.3 | Tipado y conformación | Casting de tipos, estandarización de formatos |
| 6.4 | Validación de calidad | Checks de integridad referencial, cardinalidad, duplicados |
| **7** | **Pipeline ELT con Databricks** | |
| 7.1 | Consolidación del flujo | Databricks como fuente de verdad del DW cloud |
| 7.2 | Carga Sandbox → Stage | Transformación y carga dentro de Databricks |
| 7.3 | Carga Stage → Fact-Dim | Poblamiento del modelo dimensional |
| 7.4 | Registro de logs | Evidencias de ejecución y auditoría |
| **8** | **Modelo Dimensional** | |
| 8.1 | Diseño esquema estrella | Modelo con tabla de hechos central + dimensiones |
| 8.2 | Dimensiones (8) | Tiempo, Geografía, Causa CIE-10, Sexo, Grupo Etario, Fuente, Perfil INE, Perfil IHME |
| 8.3 | Tablas de hechos (6) | fact_ine, fact_mspas, fact_who_deaths, fact_who_population, fact_panama, fact_ihme |
| **9** | **Data Warehouse en la Nube** | |
| 9.1 | Creación de esquemas | Unity Catalog `dm_mortality` |
| 9.2 | Carga del modelo dimensional | Poblamiento de tablas fact-dimension |
| 9.3 | Pruebas de consulta | Validación de queries analíticas |
| **10** | **Data Warehouse Local** | |
| 10.1 | Selección del motor | Greenplum (MPP, PostgreSQL-compatible) |
| 10.2 | Creación de esquemas | DDL para tablas fact-dimension en Greenplum |
| 10.3 | Carga del modelo | Replicación desde Databricks |
| 10.4 | Pruebas de consulta | Validación de queries locales |
| 10.5 | Backup automático | Script de respaldo del DW local |
| **11** | **Interoperabilidad Nube-Local** | |
| 11.1 | Mecanismo de intercambio | API Databricks → JDBC Greenplum |
| 11.2 | Replicación | Databricks → Greenplum para tablas Fact-Dim |
| 11.3 | Auditoría de replicación | Logs y verificación de consistencia |
| 11.4 | Validación de consistencia | Comparación de conteos y sumas entre repositorios |

### 3.3 Fase 3 — Machine Learning, BI y Cierre (Sprint 3)

| WBS | Entregable | Detalle |
|-----|-----------|---------|
| **12** | **Documentación de la Solución** | |
| 12.1 | Diagramas | Draw.io: Despliegue, Workflow, Arquitectura de Solución |
| 12.2 | Explicaciones técnicas | Documentación de decisiones de ingeniería |
| **13** | **Análisis de Datos e Insights** | |
| 13.1 | Respuesta a preguntas de negocio | 3 preguntas estratégicas PNUD/MSPAS |
| 13.2 | Gráficas analíticas | Visualizaciones en Power BI y Apache Superset |
| 13.3 | Interpretaciones de datos | Hallazgos basados en evidencia |
| **14** | **Informe Final de Consultoría** | |
| 14.1 | Resumen ejecutivo | Síntesis de hallazgos y recomendaciones |
| 14.2 | Metodología (Ágil Scrum) | Descripción del marco de trabajo |
| 14.3 | Arquitectura y sustento | Diseño y justificaciones arquitectónicas |
| 14.4 | Gobernanza y cumplimiento | Ética de datos y EU Data Act |
| 14.5 | Resultados del análisis | Insights, gráficas y explicación de hallazgos |
| 14.6 | Recomendaciones de política | Propuestas accionables para MSPAS |
| **15** | **Gestión de Proyecto** | |
| 15.1 | Project Charter | Acta de constitución (24 campos PMI) |
| 15.2 | Planificación y control | Gantt (4 meses), EDT/WBS, Matriz RACI |
| 15.3 | Gestión de riesgos | Registro de 10 riesgos con matriz P×I |
| 15.4 | Plan de aseguramiento de calidad | Estándares, roles, revisiones, métricas |
| **16** | **Propuesta Financiera** | |
| 16.1 | Estructura de costos | Tarifas por rol, días, costos de personal |
| 16.2 | Costos operativos | Infraestructura cloud, licencias, gastos administrativos |
| 16.3 | Modelo comercial | Suma alzada, desglose por hitos de pago |
| **17** | **Entregables de Comunicación** | |
| 17.1 | Presentación defensa oral | Canva/PowerPoint con demostración end-to-end |
| **18** | **Business Intelligence** | |
| 18.1 | Dashboards Power BI | 2 visualizaciones con Power Query + DAX |
| 18.2 | Dashboards Apache Superset | 2 visualizaciones SQL Native |
| **19** | **Machine Learning** | |
| 19.1 | Construcción ABT | Analytical Base Table desde el DW |
| 19.2 | Modelos entrenados | Regresión, Random Forest, K-means, Forecast |
| 19.3 | Registro MLflow | Modelos versionados en Unity Catalog |

---

## 4. Matriz RACI

La **Matriz RACI** asigna responsabilidades para cada actividad del proyecto, asegurando que no haya ambigüedad sobre quién ejecuta, aprueba, es consultado o informado. La matriz cubre **32 actividades** distribuidas en las 3 fases, cruzadas contra **8 roles**:

| Rol | Sigla |
|-----|-------|
| Gerente de Proyecto (PM) | PM |
| Arquitecto de Datos | ARQ |
| Ingeniero de Datos / ML | ING |
| Analista BI | BI |
| Consultor DBA | DBA |
| Product Owner (simulado) | PO |
| Stakeholders (PNUD/MSPAS) | STK |
| Tutor Académico (USAC) | TUT |

**Leyenda RACI:**

| Letra | Significado | Color |
|-------|-------------|-------|
| **R** | Responsible — Ejecuta la tarea | Verde |
| **A** | Accountable — Aprueba y rinde cuentas (único por actividad) | Rojo |
| **C** | Consulted — Consultado antes de ejecutar | Amarillo |
| **I** | Informed — Informado después de ejecutar | Azul |

> **Ver archivo completo:** [Matriz_RACI.xlsx](https://docs.google.com/spreadsheets/d/1ItmX3Qk2d7-Bh0uWxXh8SeXAAe-1Ds1G/edit?usp=sharing&ouid=100455211682358519319&rtpof=true&sd=true)

---

## 5. Gestión de Riesgos

Se identificaron **10 riesgos** principales clasificados por categoría, probabilidad, impacto y severidad. Cada riesgo incluye una estrategia de mitigación y un plan de contingencia con responsable asignado.

### 5.1 Resumen de Riesgos

| ID | Riesgo | Cat. | Prob. | Imp. | Sev. |
|----|--------|------|:-----:|:----:|:----:|
| R01 | RENAP no responda a tiempo la solicitud formal | Datos | 4 | 4 | **16** |
| R02 | Alto % de causas mal definidas (R99) en INE | Calidad | 3 | 4 | **12** |
| R03 | Incompatibilidad de esquemas entre fuentes heterogéneas | Técnico | 3 | 3 | 9 |
| R04 | Fallos en replicación Databricks → Greenplum | Técnico | 3 | 5 | **15** |
| R05 | Costos DBU excedan el presupuesto | Financiero | 3 | 3 | 9 |
| R06 | Incumplimiento EU Data Act (cuasi-identificadores) | Legal | 2 | 5 | **10** |
| R07 | Ausencia prolongada de miembro del equipo | Recursos | 2 | 4 | 8 |
| R08 | Cambios en APIs de fuentes externas (IHME, WHO) | Técnico | 2 | 3 | 6 |
| R09 | Problemas conectividad BI ↔ Databricks SQL Warehouse | Técnico | 2 | 3 | 6 |
| R10 | Modelos ML no alcancen métricas aceptables | Técnico | 3 | 3 | 9 |

**Severidad:** Crítico (≥12) | Moderado (8-11) | Bajo (<8)

### 5.2 Riesgos Críticos (Severidad ≥ 12)

**R01 — RENAP no responda (16):** Se mitiga enviando la solicitud en la Semana 1 con seguimiento quincenal. El plan de contingencia es utilizar INE como fuente primaria alternativa, ya que recibe los mismos registros del RENAP.

**R04 — Fallos replicación Databricks → Greenplum (15):** Se mitiga probando conectividad temprana (Semana 5) con reintentos y logs. Si falla, se generan archivos Parquet desde Databricks y se cargan manualmente en Greenplum vía COPY.

**R02 — Causas mal definidas INE (12):** Se mitiga con validación CIE-10 en ingesta y reporte de distribución. Si el porcentaje es alto, se excluyen del análisis causal principal y se documenta como limitación.

> **Ver archivo completo con matriz P×I, estrategias de mitigación y planes de contingencia:** [Gestion_Riesgos.xlsx](https://docs.google.com/spreadsheets/d/1anfpfXWvYOL2EQ5wnD5sD9YA8RBVX9Rf/edit?usp=sharing&ouid=100455211682358519319&rtpof=true&sd=true)

---

## 6. Plan de Aseguramiento de Calidad

El Plan de Aseguramiento de Calidad (Quality Assurance Plan) establece los estándares, procesos, roles y métricas que garantizan que todos los entregables del proyecto cumplan con los requisitos de calidad definidos en los Términos de Referencia y las expectativas del cliente.

### 6.1 Objetivos de Calidad

| Objetivo | Meta | Medición |
|----------|------|----------|
| Integridad de datos | ≥95% de registros fuente cargados en Sandbox | Conteo de filas fuente vs Sandbox |
| Calidad de codificación CIE-10 | ≥90% de códigos con formato válido | Validación regex en ingesta |
| Cobertura de fuentes | 5+ fuentes heterogéneas integradas | Catálogo de fuentes operativas |
| Interoperabilidad DW | Consistencia ≥99% entre DW nube y local | Comparación de sumas y conteos |
| Desempeño de modelos ML | R² ≥ 0.5 para regresión; Silueta ≥ 0.3 para clustering | Métricas en MLflow |
| Cobertura de dashboards | 2 Power BI + 2 Superset respondiendo preguntas de negocio | Checklist de requerimientos |
| Documentación | MkDocs desplegado con todas las secciones requeridas | Revisión de completitud |
| Cumplimiento ético | 0 exposiciones de datos individuales en visualizaciones | Auditoría de dashboards |

### 6.2 Roles y Responsabilidades de Calidad

| Rol | Responsabilidad |
|-----|----------------|
| **Gerente de Proyecto** | Dueño del plan de calidad. Aprueba entregables. Coordina revisiones y auditorías. |
| **Arquitecto de Datos** | Revisa diseño de arquitectura, modelo dimensional, DDL. Responsable de la calidad técnica del DW. |
| **Ingeniero de Datos / ML** | Ejecuta pruebas de calidad de datos (validación CIE-10, nulos, duplicados). Responsable de métricas de modelos ML. |
| **Analista BI** | Valida que los dashboards respondan las preguntas de negocio. Revisa que no se expongan datos individuales. |
| **Consultor DBA** | Responsable de la consistencia en la replicación Databricks → Greenplum. Ejecuta auditorías de interoperabilidad. |
| **Tutor USAC** | Revisor externo. Proporciona retroalimentación en cada Sprint Review. |

### 6.3 Procesos de Control de Calidad

#### 6.3.1 Calidad de Datos (Fases 1 y 2)

- **Validación de formato CIE-10:** Todo código de causa debe cumplir el patrón `^[A-Z][0-9]{2}[0-9A-Z]?$`. Códigos inválidos se marcan como `null` y se reportan.
- **Deduplicación:** Se aplica `dropDuplicates()` sobre llave natural compuesta al final de cada ingesta.
- **Validación de dominios:** Años en rango 2000–2030. Edad en rango [0, 120]. Sexo en valores esperados. Valores fuera de dominio se marcan como `null`.
- **Reporte de calidad:** Cada notebook genera un resumen de filas ingresadas, rechazadas, nulos por columna y causas inválidas.

#### 6.3.2 Calidad de Código

- **Control de versiones:** Todo el código se versiona en GitHub. Commits atómicos con mensajes descriptivos. Se utiliza `git blame` para trazabilidad de contribuciones.
- **Code Review:** Revisión entre pares antes de merge a `main`. El revisor verifica legibilidad, cumplimiento de estándares y ausencia de secrets hardcodeados.
- **Secrets Management:** Todas las credenciales se gestionan mediante Databricks Secret Scopes. No se permite hardcodear tokens, claves o contraseñas en notebooks.

#### 6.3.3 Calidad de Modelos ML (Fase 3)

- **Train/Test Split:** 80/20 para todos los modelos. Validación cruzada k-fold (k=5) para Random Forest.
- **Baseline:** Se establece un modelo naïve (promedio histórico) como línea base de comparación.
- **Registro MLflow:** Cada experimento se registra con parámetros, métricas y artefactos. Solo los modelos que superan el baseline se registran en Model Registry.
- **Métricas mínimas:** Regresión R² ≥ 0.5. Clustering Silhouette Score ≥ 0.3. Clasificación F1 ≥ 0.7.

#### 6.3.4 Calidad de Dashboards BI (Fase 3)

- **Validación de datos:** Cada gráfica se compara contra una consulta SQL directa al DW para verificar que los valores mostrados sean correctos.
- **Revisión de privacidad:** Se audita que ningún dashboard muestre datos a nivel municipal o individual. Solo agregados departamentales, por grupo etario y causa.
- **Checklist de preguntas de negocio:** Cada dashboard debe responder al menos una de las preguntas estratégicas definidas en los Términos de Referencia.

#### 6.3.5 Calidad de Documentación

- **MkDocs:** La documentación se despliega automáticamente con GitHub Actions en cada push a `main`.
- **Estructura:** Debe incluir todas las secciones requeridas: arquitectura, fuentes, pipeline, gobernanza, modelo dimensional, source-to-target mapping, insights, administración y propuesta financiera.
- **Diagramas:** Formato Draw.io exclusivamente. 4 vistas requeridas: Solución, Despliegue, Sandbox, Stage, Fact-Dimensions.

### 6.4 Auditorías y Revisiones

| Momento | Tipo | Responsable | Criterio de Aceptación |
|---------|------|-------------|------------------------|
| Fin de cada notebook | Autoverificación | Ingeniero de Datos | Resumen de calidad sin errores críticos |
| Antes de merge a main | Code Review | Par del equipo | Aprobación de al menos 1 revisor |
| Fin de Sprint (Sprint Review) | Demostración end-to-end | Todo el equipo | Flujo completo funcional desde fuente hasta entregable |
| Pre-entrega de fase | Revisión de cumplimiento | PM + Tutor | Checklist de entregables completo |
| Cierre del proyecto | Auditoría final | PM | Todos los entregables aprobados, documentación desplegada |

### 6.5 Herramientas de Calidad

| Herramienta | Propósito |
|-------------|-----------|
| **GitHub** | Control de versiones, code review, trazabilidad (`git blame`) |
| **Databricks Notebooks** | Ejecución y documentación de pipelines con celdas de validación |
| **MLflow** | Tracking de experimentos ML, registro de métricas y artefactos |
| **Power BI / Superset** | Validación visual de datos agregados |
| **MkDocs + GitHub Actions** | Despliegue automatizado de documentación |
| **Draw.io** | Diagramas de arquitectura y modelo de datos |

### 6.6 Métricas de Calidad (Dashboard de Control)

| Indicador | Frecuencia | Responsable |
|-----------|------------|-------------|
| % de registros fuente cargados en Sandbox | Por ingesta | Ing. Datos |
| % de códigos CIE-10 válidos | Por ingesta | Ing. Datos |
| % de valores nulos por columna crítica | Por ingesta | Ing. Datos |
| Consistencia DW nube vs local (diferencia %) | Por replicación | DBA |
| Métricas de modelos ML (R², Silueta, F1) | Por experimento | Ing. Datos |
| Cobertura de documentación (% secciones completas) | Semanal | PM |
| Cumplimiento de cronograma (% avance vs plan) | Semanal | PM |

---

*Documento elaborado como parte de los entregables de la Fase 3 del proyecto.*  
*Seminario de Sistemas 2 — USAC, Escuela de Vacaciones 2026.*
