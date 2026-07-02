.PHONY: up down backup replication-preflight check-pipeline-runs check-pipeline-runs-dry-run test-databricks replicate-dimensions replicate-dimensions-limit replicate-facts replicate-facts-limit replicate-all replicate-all-limit replicate-dim-tiempo replicate-dim-tiempo-limit

up:
	@docker compose up -d
	@sleep 40s
	@docker exec -i -u gpadmin dw-greenplum /usr/local/greenplum-db/bin/psql -h localhost -U gpadmin -d postgres -f - < init.sql

down:
	@docker compose down -v

backup:
	@GREENPLUM_HOST=$${GREENPLUM_HOST:-localhost} \
	 GREENPLUM_PORT=$${GREENPLUM_PORT:-5432} \
	 GREENPLUM_DB=$${GREENPLUM_DB:-dw_semis2} \
	 GREENPLUM_USER=$${GREENPLUM_USER:-gpadmin} \
	 ./backup_greenplum.sh

replication-preflight:
	@python3 replication/replicate.py --preflight

check-pipeline-runs:
	@python3 replication/check_pipeline_runs.py

check-pipeline-runs-dry-run:
	@python3 replication/check_pipeline_runs.py --dry-run

test-databricks:
	@python3 replication/replicate.py --test-databricks --table semi2.dm_mortality.dim_genero

replicate-dim-genero:
	@python3 replication/replicate.py --table semi2.dm_mortality.dim_genero

replicate-dim-genero-limit:
	@python3 replication/replicate.py --table semi2.dm_mortality.dim_genero --limit 100

replicate-dimensions:
	@python3 replication/replicate.py --group dimensions

replicate-dimensions-limit:
	@python3 replication/replicate.py --group dimensions --limit 100

replicate-facts:
	@python3 replication/replicate.py --group facts

replicate-facts-limit:
	@python3 replication/replicate.py --group facts --limit 100

replicate-all:
	@python3 replication/replicate.py --all

replicate-all-limit:
	@python3 replication/replicate.py --all --limit 100

replicate-dim-tiempo:
	@python3 replication/replicate.py --table semi2.dm_mortality.dim_tiempo

replicate-dim-tiempo-limit:
	@python3 replication/replicate.py --table semi2.dm_mortality.dim_tiempo --limit 100

#Para entrar al contenedor
# docker exec -it -u gpadmin dw-greenplum bash
# psql -d postgres

# \dn #Para ver los esquemas
# \l #Para ver las base de datos


#Instalar Bore
# cargo install bore-cli
# bore local 5432 --to bore.pub
# Luego solo tienen que copiar el puerto que les dio y ponerlo en databricks :)
