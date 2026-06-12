## data_sources (fuentes dispersas para ELT)

Este proyecto incluye un comando ELT que copia archivos “tal cual” desde una estructura
de carpetas dispersa hacia `data_lake/raw/`.

### Estructura base (anexo completo)

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

### Cargas incrementales — Día 1 y Día 2 (rúbrica Evaluación)

Carpetas listas para la demostración obligatoria (≥5 registros por archivo, un día por lote):

| Carpeta | Fecha simulada | Contenido |
|---------|----------------|-----------|
| `dia_1/` | 2026-04-01 | Todas las fuentes obligatorias + opcionales |
| `dia_2/` | 2026-04-02 | Nuevo lote (ventas y dimensiones del día 2) |

**Demo limpia (recomendada para la presentación):** si ya cargaste datos de prueba anteriores,
reinicia el DW y el maestro antes de grabar la evidencia Día 1 → Día 2:

```powershell
docker compose exec backend python manage.py shell -c "from core.models import FactVentas; FactVentas.objects.all().delete(); print('FactVentas vacía')"
# Opcional: borrar data_lake/raw/* y processed/ventas_unificadas_maestro.csv en el host
```

**Demo recomendada (un comando por día):**

```powershell
docker compose exec backend python manage.py run_incremental_day --day dia_1 --ingest-date 2026-04-01
docker compose exec backend python manage.py audit_pipeline

docker compose exec backend python manage.py run_incremental_day --day dia_2 --ingest-date 2026-04-02
docker compose exec backend python manage.py audit_pipeline
```

Tras Día 1 espera ~10 hechos en `FactVentas`; tras Día 2 ~20 (5 POS + 5 online por día).

**Paso a paso (mismo resultado):**

```powershell
# Día 1
docker compose exec backend python manage.py run_elt_ingest --sources-root /data_sources/dia_1 --ingest-date 2026-04-01
docker compose exec backend python manage.py run_etl --append-master
docker compose exec backend python manage.py load_dw --incremental --ventas-file maestro

# Día 2
docker compose exec backend python manage.py run_elt_ingest --sources-root /data_sources/dia_2 --ingest-date 2026-04-02
docker compose exec backend python manage.py run_etl --append-master
docker compose exec backend python manage.py load_dw --incremental --ventas-file maestro
docker compose exec backend python manage.py audit_pipeline
```

- `run_etl --append-master` mantiene `data_lake/processed/ventas_unificadas_maestro.csv` (acumula, dedup `id_venta`+`canal`).
- `load_dw --incremental` **no borra** hechos previos (histórico preservado).
- `audit_pipeline` evidencia crecimiento en raw, processed y `FactVentas` por día/mes/año.

Ver también comandos en la web: **/flow/** o **/analytics/**.

### Ejecutar ELT completo (anexo de una vez)

```powershell
docker compose exec backend python manage.py run_elt_ingest
docker compose exec backend python manage.py run_etl
docker compose exec backend python manage.py load_dw
```

El ETL escribe CSV en `data_lake/processed/` (incluye fuentes opcionales limpias; el modelo
estrella en Postgres sigue usando ventas + dimensiones obligatorias).
