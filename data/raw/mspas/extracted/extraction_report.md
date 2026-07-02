# Reporte de Extracción — PDFs MSPAS

Los archivos MSPAS descargados son documentos PDF con extensión `.xlsx`.
Su contenido es principalmente gráficas de barras/líneas. Solo se pudo extraer
el texto de los ejes y una tabla estructurada.

## Archivos generados

### mspas_mortalidad_general_2010_2024.csv
- **Filas extraídas:** 15
- **Archivo:** `mspas_mortalidad_general_2010_2024.csv`
- **Nota:** Totales anuales de defunciones extraídos del texto de la gráfica 'Mortalidad General 2010-2024'.

### mspas_exceso_mortalidad_2022.csv
- **Filas extraídas:** 5
- **Archivo:** `mspas_exceso_mortalidad_2022.csv`
- **Nota:** Tabla estructurada de exceso de mortalidad 2022 (observado vs esperado por grupo etario y sexo).

### mspas_tasa_mortalidad_2001_2019.csv
- **Filas extraídas:** 19
- **Archivo:** `mspas_tasa_mortalidad_2001_2019.csv`
- **Nota:** Tasas de mortalidad general por año extraídas del eje Y de la gráfica 'Mortalidad General 2001-2019'.

## Lo que NO pudo extraerse

- `top15_causas_mortalidad_ine.xlsx`: tablas con muchas celdas fusionadas e ilegibles por pdfplumber. Requiere revisión manual.
- Desgloses por departamento: no disponibles en estos PDFs (datos nacionales únicamente).
- Totales de defunciones 2001-2014: están en gráficas de barra sin etiquetas de valor en el texto.

## Recomendación

Para datos nacionales 2001-2019 con granularidad de causa, usar directamente los
microdatos INE disponibles en `data/raw/ine/` (2015-2024) y complementar con WHO
para años anteriores a 2015.
