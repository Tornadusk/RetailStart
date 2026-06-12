## simulacion_semana (legacy)

> **Para la rúbrica Evaluación use `data_sources/dia_1/` y `data_sources/dia_2/`**
> (carga incremental Día 1 → Día 2). Ver `data_sources/README.md`.

La carpeta `lote_2/` se mantiene como ejemplo extra de días 06–08 abril.
Comando alternativo (solo ventas, sin todas las fuentes):

```powershell
docker compose exec backend python manage.py ingest_sales_batch --batch lote_2 --ingest-date 2026-04-08
docker compose exec backend python manage.py run_etl --append-master
docker compose exec backend python manage.py load_dw --incremental --ventas-file maestro
```
