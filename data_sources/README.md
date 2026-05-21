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
