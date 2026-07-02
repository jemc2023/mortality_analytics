SELECT table_name, concat('SHOW CREATE TABLE ', table_catalog, '.', table_schema, '.', table_name, ';') AS ejecutar_comando
FROM semi2.information_schema.tables
WHERE table_schema = 'stage';