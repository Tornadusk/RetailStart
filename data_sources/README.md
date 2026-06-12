## data_sources (fuentes dispersas para ELT)

Este proyecto incluye un comando ELT que copia archivos “tal cual” desde una estructura
de carpetas dispersa hacia `data_lake/raw/`.

### Estructura esperada

Coloca tus archivos en estas rutas (relativas a `data_sources/`):

**Obligatorios (anexo):**

- `sistemas_legacy/pos/ventas_pos.csv`
- `marketplace/ventas_online.csv`
- `crm_export/clientes_crm.csv`
- `erp_snapshot/productos_erp.csv`

**Opcionales (anexo — integrados en el repo):**

- `mobile_analytics/eventos_app.json`
- `sistemas_legacy/proveedor_logistica/logistica.xml`
- `infra_logs/logs_sistema.txt`
- `crm_export/callcenter.csv`
- `marketing_analytics/redes_sociales.json`
- `erp_snapshot/proveedores.csv`
- `catalogo_multimedia/multimedia.csv`

### Ejecutar ELT (dentro de Docker)

```powershell
docker compose exec backend python manage.py run_elt_ingest
docker compose exec backend python manage.py run_etl
```

El ETL escribe CSV en `data_lake/processed/` (incluye fuentes opcionales limpias; el modelo
estrella en Postgres sigue usando ventas + dimensiones obligatorias).

### Carga incremental (acumular días lote a lote)

Para demostrar cómo `FactVentas` recopila y ordena la información por día/mes/año:

```powershell
# Carga inicial con archivo maestro acumulativo
docker compose exec backend python manage.py run_elt_ingest --ingest-date 2026-04-05
docker compose exec backend python manage.py run_etl --append-master
docker compose exec backend python manage.py load_dw --incremental --ventas-file maestro
docker compose exec backend python manage.py audit_pipeline

# Lote de días nuevos (ver simulacion_semana/README.md)
docker compose exec backend python manage.py ingest_sales_batch --batch lote_2 --ingest-date 2026-04-08
docker compose exec backend python manage.py run_etl --append-master
docker compose exec backend python manage.py load_dw --incremental --ventas-file maestro
docker compose exec backend python manage.py audit_pipeline
```

- `run_etl --append-master` mantiene `data_lake/processed/ventas_unificadas_maestro.csv`
  (acumula días, deduplica por `id_venta` + `canal`).
- `load_dw --incremental` hace upsert de hechos sin borrar la historia previa.
- `audit_pipeline` muestra conteos por capa (raw → maestro → FactVentas por día/mes/año).
