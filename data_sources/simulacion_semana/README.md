## simulacion_semana (lotes de ventas para carga incremental)

Cada subcarpeta es un **lote** de ventas nuevas (días adicionales) que simula la
llegada de datos frescos. Solo contiene los archivos que cambian día a día:

- `ventas_pos.csv`
- `ventas_online.csv`

Las dimensiones (clientes, productos) no se repiten aquí: ya viven en
`data_sources/` y se cargan una sola vez con `run_elt_ingest`.

### Lotes disponibles

| Lote | Días que aporta |
|------|-----------------|
| `lote_2/` | 2026-04-06, 2026-04-07, 2026-04-08 |

El anexo base (`data_sources/sistemas_legacy/pos/ventas_pos.csv` y
`marketplace/ventas_online.csv`) cubre 2026-04-01 … 2026-04-05.

### Demostración de carga incremental (Docker)

```powershell
# 1) Carga inicial (anexo: 04-01 .. 04-05)
docker compose exec backend python manage.py run_elt_ingest --ingest-date 2026-04-05
docker compose exec backend python manage.py run_etl --append-master
docker compose exec backend python manage.py load_dw --incremental --ventas-file maestro
docker compose exec backend python manage.py audit_pipeline      # foto inicial

# 2) Lote nuevo (04-06 .. 04-08): la tabla de hechos crece, los días previos siguen
docker compose exec backend python manage.py ingest_sales_batch --batch lote_2 --ingest-date 2026-04-08
docker compose exec backend python manage.py run_etl --append-master
docker compose exec backend python manage.py load_dw --incremental --ventas-file maestro
docker compose exec backend python manage.py audit_pipeline      # FactVentas mayor
```

Para crear un lote nuevo: duplica `lote_2/`, renómbralo (ej. `lote_3/`) y ajusta
las fechas/filas de los dos CSV.
