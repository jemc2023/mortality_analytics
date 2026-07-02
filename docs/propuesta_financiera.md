# Propuesta Financiera — Plataforma Analítica de Mortalidad End-to-End

> **Cliente:** PNUD · Ministerio de Salud Pública y Asistencia Social (MSPAS)  
> **Firma Consultora:** DataMortality Analytics Group  
> **Modalidad:** Consultoría de resultado fijo (suma alzada, todo incluido)  
> **Duración:** 4 meses | **Tipo de contrato:** Precio fijo por hitos  
> **Moneda:** Dólares estadounidenses (USD) — aplica tipo de cambio referencial Q7.75/USD

---

## 1. Resumen Ejecutivo

La presente propuesta cubre el diseño, construcción y entrega de una **plataforma analítica de datos de mortalidad de punta a punta (End-to-End PoC)** en tres fases acumulativas. El sistema integra fuentes de datos heterogéneas (INE, MSPAS, IHME, OMS, INEC Panamá, RENAP), implementa un pipeline ELT sobre **Databricks / AWS**, consolida un Data Warehouse híbrido (nube + local Greenplum), aplica modelos de Machine Learning (sklearn + MLflow) y entrega visualizaciones analíticas en Power BI y Apache Superset.

El precio de la consultoría se cotiza como **suma alzada todo incluido**, desglosado por rol, producto e hito de pago.

---

## 2. Alcance del Trabajo

| Fase | Producto | Descripción |
|------|---------|-------------|
| **Fase 1** | Ingesta y Sandbox | Conectores a 5+ fuentes heterogéneas (Google Drive, OneDrive/SharePoint, AWS S3, RDS PostgreSQL, Nginx), carga al sandbox `workspace.sandbox.*` en Databricks Delta Lake, diccionario de datos y plan de anonimización (EU Data Act). |
| **Fase 2** | ELT y Data Warehouse | Pipeline Sandbox → Stage → Fact-Dimensiones (modelo estrella, 5 hechos + 5 dimensiones), DW en la nube (Databricks Unity Catalog `workspace.dm_mortality`) y DW local (Greenplum), interoperabilidad vía API Databricks → replicación. |
| **Fase 3** | ML, BI y Cierre | 4 modelos ML (Regresión Lineal exceso, Random Forest drivers, K-means segmentación, pronóstico), tracking MLflow + Unity Catalog, 2 dashboards Power BI + 2 Superset, análisis pre/post-COVID, documentación final. |

---

## 3. Contrataciones Necesarias

Se requieren **5 roles funcionales**, cubiertos por 3 consultores de planta y 1 especialista subcontratado a tiempo parcial:

### 3.1 Descripción de Roles

| # | Rol | Justificación Técnica |
|---|-----|----------------------|
| 1 | **Gerente de Proyecto (PM)** | Coordinación con cliente (PNUD/MSPAS), control de cronograma, WBS, informes de avance, preparación de las defensas orales y entrega de documentación final. Cobertura transversal a las 3 fases. |
| 2 | **Arquitecto de Datos / Lead Engineer** | Diseño de la arquitectura híbrida (Databricks on AWS + Greenplum), diseño del esquema estrella (DDL), diseño de los pipelines ELT, configuración del workspace y Unity Catalog, gestión de Secret Scopes y seguridad. |
| 3 | **Ingeniero de Datos ETL/ELT & ML** | Implementación de conectores (GDrive API, Microsoft Graph/SharePoint, boto3/S3, JDBC/RDS, HTTP/Nginx), notebooks de staging, construcción del ABT, entrenamiento de 4 modelos con sklearn + MLflow, registro en Model Registry. |
| 4 | **Analista de BI y Visualización** | Construcción de dashboards Power BI (Power Query + DAX), dashboards Apache Superset, análisis comparativo pre/post-COVID, recomendaciones de política basadas en evidencia. Activo en Fase 3. |
| 5 | **Consultor DBA (subcontratado parcial)** | Implementación del DW local Greenplum (MPP), script de replicación Databricks → Greenplum, DDL Oracle-compatible, configuración de particionamiento y auditoría de consistencia entre repositorios. |

---

## 4. Tarifas y Días por Rol

| Rol | Tipo | Tarifa USD/día | Días Fase 1 | Días Fase 2 | Días Fase 3 | **Total Días** |
|-----|------|---------------|:-----------:|:-----------:|:-----------:|:--------------:|
| Gerente de Proyecto | Planta | $400 | 22 | 22 | 44 | **88** |
| Arquitecto de Datos | Planta | $550 | 22 | 22 | 30 | **74** |
| Ingeniero Datos / ML | Planta | $450 | 22 | 22 | 44 | **88** |
| Analista BI | Planta | $375 | 0 | 10 | 44 | **54** |
| Consultor DBA | Subcontratado | $375 | 0 | 15 | 5 | **20** |

> **Base de cálculo:** 22 días hábiles/mes. Fase 1 = Mes 1, Fase 2 = Mes 2, Fase 3 = Meses 3-4.

---

## 5. Costos de Personal

### 5.1 Por Fase

#### Fase 1 — Ingesta y Sandbox (Mes 1, 22 días)

| Rol | Días | Tarifa/día | Subtotal |
|-----|:----:|----------:|--------:|
| Gerente de Proyecto | 22 | $400 | $8,800 |
| Arquitecto de Datos | 22 | $550 | $12,100 |
| Ingeniero Datos / ML | 22 | $450 | $9,900 |
| **Subtotal Fase 1** | | | **$30,800** |

#### Fase 2 — ELT y Data Warehouse (Mes 2, 22 días)

| Rol | Días | Tarifa/día | Subtotal |
|-----|:----:|----------:|--------:|
| Gerente de Proyecto | 22 | $400 | $8,800 |
| Arquitecto de Datos | 22 | $550 | $12,100 |
| Ingeniero Datos / ML | 22 | $450 | $9,900 |
| Analista BI (onboarding) | 10 | $375 | $3,750 |
| Consultor DBA | 15 | $375 | $5,625 |
| **Subtotal Fase 2** | | | **$40,175** |

#### Fase 3 — ML, BI y Cierre (Meses 3-4, 44 días)

| Rol | Días | Tarifa/día | Subtotal |
|-----|:----:|----------:|--------:|
| Gerente de Proyecto | 44 | $400 | $17,600 |
| Arquitecto de Datos | 30 | $550 | $16,500 |
| Ingeniero Datos / ML | 44 | $450 | $19,800 |
| Analista BI | 44 | $375 | $16,500 |
| Consultor DBA | 5 | $375 | $1,875 |
| **Subtotal Fase 3** | | | **$72,275** |

### 5.2 Resumen de Personal

| Rol | Días totales | Tarifa/día | **Total** |
|-----|:-----------:|----------:|--------:|
| Gerente de Proyecto | 88 | $400 | $35,200 |
| Arquitecto de Datos | 74 | $550 | $40,700 |
| Ingeniero Datos / ML | 88 | $450 | $39,600 |
| Analista BI | 54 | $375 | $20,250 |
| Consultor DBA | 20 | $375 | $7,500 |
| **TOTAL PERSONAL** | **324 días-persona** | | **$143,250** |

---

## 6. Costos Operativos

### 6.1 Infraestructura en la Nube

| Componente | Descripción | Costo/mes | Meses | **Total** |
|-----------|-------------|----------:|:-----:|--------:|
| **Databricks on AWS** | All-Purpose Compute (4 cores, 16GB RAM) + SQL Warehouse Serverless. ~4 h/día × 88 días hábiles, ~1.5 DBU/h promedio. | $120 | 4 | $480 |
| **AWS S3** | Almacenamiento de datos crudos (`raw/`), artefactos ML (modelos, ABT, predicciones en `ml/`), respaldos. ~100 GB total. | $15 | 4 | $60 |
| **AWS RDS PostgreSQL** | Instancia `db.t3.micro`, esquema `raw_data`, fuente MSPAS. Ingesta JDBC desde Databricks. | $25 | 4 | $100 |
| **AWS EC2 (Nginx)** | Instancia `t3.micro` para servidor web local expuesto con DevTunnel; sirve archivos WHO Mortality. | $15 | 4 | $60 |
| **AWS Data Transfer** | Egress S3 → Databricks, snapshots, sync artefactos ML. | $5 | 4 | $20 |
| **MLflow / Unity Catalog** | Incluido en el workspace Databricks. | — | — | $0 |
| **Subtotal Nube** | | | | **$720** |

### 6.2 Software y Licencias

| Herramienta | Uso | Modalidad | Costo/mes | Meses | **Total** |
|------------|-----|-----------|----------:|:-----:|--------:|
| **Power BI Pro** | 2 dashboards analíticos (Power Query + DAX), conexión directa al SQL Warehouse de Databricks. 3 licencias. | Suscripción mensual × 3 usuarios | $10 | 4 | $120 |
| **Apache Superset** | 2 dashboards BI complementarios (segunda herramienta). Open-source, auto-alojado en EC2. | Código abierto | $0 | — | $0 |
| **Greenplum Community** | DW local MPP, Open Source, basado en PostgreSQL. | Código abierto | $0 | — | $0 |
| **GitHub (Actions + Pages)** | Repositorio del código, CI/CD para MkDocs. Free tier público. | Código abierto | $0 | — | $0 |
| **MkDocs Material** | Documentación técnica desplegada vía GitHub Actions. | Código abierto | $0 | — | $0 |
| **DevTunnel (Nginx)** | Túnel para exponer el servidor Nginx local a Databricks en la nube. | Free tier | $0 | — | $0 |
| **Microsoft DevTunnel / Graph API** | Acceso a SharePoint/OneDrive para fuente Panamá. App registration Azure AD. | Free tier | $0 | — | $0 |
| **Google Drive API** | Acceso programático a `semis2_raw_data/ine/` (fuente INE). Service account. | Free tier | $0 | — | $0 |
| **Subtotal Licencias** | | | | | **$120** |

### 6.3 Gastos Administrativos y Operativos

| Concepto | Detalle | **Monto** |
|---------|---------|----------:|
| Reuniones con cliente | Videoconferencias, sesiones de revisión con PNUD/MSPAS, presentación de defensas (4 reuniones presenciales + 8 virtuales) | $400 |
| Materiales de presentación | Impresión de informes, diapositivas, encuadernación documentación final | $150 |
| Herramientas de comunicación | Zoom Pro / Teams (4 meses) | $60 |
| Gastos administrativos de la firma | Gestión contractual, facturación, reportes (5% del costo de personal) | $7,163 |
| Contingencia operativa (3% infra) | Sobrecostos imprevistos en servicios cloud, aumento de uso de DBUs | $250 |
| **Subtotal Operativos** | | **$8,023** |

### 6.4 Resumen Costos Operativos

| Categoría | Total |
|-----------|------:|
| Infraestructura en la nube | $720 |
| Software y licencias | $120 |
| Gastos administrativos y operativos | $8,023 |
| **Total Costos Operativos** | **$8,863** |

---

## 7. Suma Alzada — Todo Incluido

| Concepto | Monto (USD) | % del total |
|---------|------------:|:-----------:|
| Costos de personal | $143,250 | 76.5% |
| Costos operativos (infraestructura + licencias + admin) | $8,863 | 4.7% |
| **Subtotal directo** | **$152,113** | **81.2%** |
| Overhead corporativo (12%) | $18,254 | 9.7% |
| Margen de utilidad (10%) | $17,036 | 9.1% |
| **PRECIO TOTAL (SUMA ALZADA)** | **$187,403** | **100%** |

> **Precio contratado: USD $187,400** (ciento ochenta y siete mil cuatrocientos dólares)  
> Equivalente referencial: **Q 1,452,350** (tipo de cambio Q7.75/USD)

El precio cubre **todo** el personal, infraestructura, licencias, gastos administrativos, overhead y utilidad de la firma. No aplican cobros adicionales por concepto de horas extra, uso de herramientas cloud dentro del alcance descrito, ni comunicaciones con el cliente.

---

## 8. Desglose por Producto / Hito de Pago

Los pagos se liberan contra entrega y aprobación de cada hito. El criterio de aprobación es la demostración oral end-to-end del flujo completo hasta el hito correspondiente.

| # | Hito | Producto entregable | % | Monto (USD) | Fecha estimada |
|---|------|-------------------|:-:|------------:|:--------------:|
| **0** | **Anticipo** | Firma del contrato + kick-off. Provisión de accesos a infraestructura (cuentas cloud, repositorio). | 15% | $28,110 | Día 0 |
| **1** | **Fase 1 — Sandbox** | Conectores operativos (Google Drive, SharePoint, S3, RDS, Nginx). Sandbox `workspace.sandbox.*` poblado (≥5 fuentes). Diccionario de datos. Plan de anonimización EU Data Act. Arquitectura de despliegue (Draw.io 4 vistas). | 25% | $46,850 | Fin Mes 1 |
| **2** | **Fase 2 — Data Warehouse** | Pipeline ELT completo (Sandbox → Stage → Fact-Dimensiones). DW en la nube (`workspace.dm_mortality.*`, ≥5 tablas de hechos + 5 dimensiones). DW local Greenplum poblado e interoperable. Script de replicación validado. | 25% | $46,850 | Fin Mes 2 |
| **3** | **Fase 3 — ML y BI** | 4 modelos ML entrenados y registrados en MLflow + Unity Catalog (`pred_exceso`, `pred_rf_importancias`, `pred_clusters_departamento`, `pred_forecast`). 2 dashboards Power BI + 2 dashboards Superset. Análisis pre/post-COVID con recomendaciones de política. | 30% | $56,220 | Fin Mes 4 |
| **4** | **Cierre** | Documentación técnica final (MkDocs desplegado). Project Charter: Diagrama de Gantt, WBS, fechas de entrega. Informe ejecutivo de la consultoría. Transferencia de conocimiento al cliente. | 5% | $9,370 | +15 días tras Fase 3 |
| | **TOTAL** | | **100%** | **$187,400** | |

---

## 9. Notas y Condiciones

1. **Alcance fijo:** el precio es suma alzada. No se cobran extras por actividades incluidas en el alcance descrito en la sección 2.
2. **Cambios de alcance:** cualquier funcionalidad no descrita en este documento debe ser aprobada por escrito mediante una orden de cambio con ajuste de precio.
3. **Infraestructura:** los costos cloud están calculados para uso PoC (cargas controladas, clusters apagados fuera del horario de trabajo). Un despliegue productivo 24/7 requeriría revisión de costos.
4. **Herramientas open-source:** Greenplum, Apache Superset, MkDocs y Nginx no generan costos de licencia. El cliente es responsable del hardware local para Greenplum.
5. **Datos y privacidad:** todos los datos se manejan de forma anonimizada/agregada según el EU Data Act. El cliente provee autorización formal para el uso de datos de MSPAS e INE.
6. **Moneda y pago:** pagos en USD, transferencia bancaria, 30 días netos desde aprobación del hito.
7. **Validez de la oferta:** 30 días calendario desde la fecha de emisión.

---

## 10. Estructura de Equipo y Dedicación

```
Mes 1 (Fase 1)          Mes 2 (Fase 2)          Mes 3-4 (Fase 3)
────────────────────    ────────────────────    ────────────────────────
PM              ████    PM              ████    PM              ████████
Arquitecto      ████    Arquitecto      ████    Arquitecto      ██████░░
Ing. Datos/ML   ████    Ing. Datos/ML   ████    Ing. Datos/ML   ████████
BI Analyst      ░░░░    BI Analyst      ██░░    BI Analyst      ████████
DBA             ░░░░    DBA             ███░    DBA             █░░░░░░░

█ = Activo   ░ = No activo / parcial
```

---

*Documento elaborado como parte de los entregables de la Fase 3 del proyecto Seminario de Sistemas 2, USAC — Escuela de Vacaciones 2026.*  
*Elaborado: 2026-06-25*
