.PHONY: up down init setup post-setup db status export all

# Credenciales de Superset — sobreescribir con make SUPERSET_USER=... o export
SUPERSET_USER ?= admin
SUPERSET_PASS ?= admin
SUPERSET_EMAIL ?= admin@superset.com
SUPERSET_HOST ?= localhost
SUPERSET_PORT ?= 8088
GREENPLUM_HOST ?= dw-greenplum
GREENPLUM_PORT ?= 5432
GREENPLUM_DB ?= dw_semis2
GREENPLUM_USER ?= gpadmin
GREENPLUM_PASS ?= semis2_grupo11

up:
	@docker compose up -d
	@sleep 60s

down:
	@docker compose down -v

init:
	@docker exec bi-superset superset fab create-admin \
		--username $(SUPERSET_USER) \
		--password $(SUPERSET_PASS) \
		--firstname Admin \
		--lastname User \
		--email $(SUPERSET_EMAIL)
	@docker exec bi-superset superset db upgrade
	@docker exec bi-superset superset init

db:
	@docker exec bi-superset superset set-database-uri \
		-d "Greenplum DW" \
		-u "postgresql://$(GREENPLUM_USER):$(GREENPLUM_PASS)@$(GREENPLUM_HOST):$(GREENPLUM_PORT)/$(GREENPLUM_DB)"

setup:
	@cd .. && PYTHONPATH=. python3 -m bi.setup.setup_superset

post-setup:
	@cd .. && PYTHONPATH=. python3 -m bi.setup.post_setup

all: up init db setup post-setup
	@echo "=== Superset listo. Drag charts en UI para asociarlos a dashboards ==="

status:
	@docker compose ps
	@echo "---"
	@curl -s -o /dev/null -w "Superset HTTP status: %{http_code}\n" http://$(SUPERSET_HOST):$(SUPERSET_PORT)/health

export:
	@cd .. && PYTHONPATH=. python3 -m bi.setup.export_dashboards

#Para entrar al contenedor de Superset
# docker exec -it bi-superset bash

#Para acceder a Superset UI
# http://localhost:8088
# Credenciales por defecto: admin / admin
