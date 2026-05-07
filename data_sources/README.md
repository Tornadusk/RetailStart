## data_sources (fuentes dispersas para ELT)

Este proyecto incluye un comando ELT que copia archivos “tal cual” desde una estructura
de carpetas dispersa hacia `data_lake/raw/`.

### Estructura esperada

Coloca tus archivos en estas rutas (relativas a `data_sources/`):

- `sistemas_legacy/pos/ventas_pos.csv`
- `marketplace/ventas_online.csv`
- `crm_export/clientes_crm.csv`
- `erp_snapshot/productos_erp.csv`
- `mobile_analytics/eventos_app.json`
- `proveedor_logistica/logistica.xml`
- `infra_logs/logs_sistema.txt`

### Ejecutar ELT (dentro de Docker)

```powershell
docker compose exec backend python manage.py run_elt_ingest
```

