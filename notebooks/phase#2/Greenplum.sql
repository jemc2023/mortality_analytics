DROP CATALOG IF EXISTS dw_semis2_virtual;
DROP CONNECTION IF EXISTS puente_greenplum_local;

CREATE CONNECTION puente_greenplum_local
TYPE postgresql
OPTIONS (
  host secret('semis2_scope', 'DW_host'),
  port secret('semis2_scope', 'DW_port'),       
  user secret('semis2_scope', 'DW_user'),       
  password secret('semis2_scope', 'DW_pass'),       
);

CREATE FOREIGN CATALOG dw_semis2_virtual
USING CONNECTION puente_greenplum_local
OPTIONS (database 'dw_semis2');

GRANT ALL PRIVILEGES ON CATALOG dw_semis2_virtual TO `teamatetoshare@gmail.com`;

SELECT * FROM dw_semis2_virtual.dm_mortality.alumno;
