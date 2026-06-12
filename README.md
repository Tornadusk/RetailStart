# RetailStart (Django + Postgres + Nginx + Docker)

Este proyecto levanta una web en **Django** dentro de Docker, usando **Postgres** (solo para Django) y **Nginx** como “front”:

- Nginx funciona como **reverse proxy** hacia Django/Gunicorn.
- Nginx sirve los **archivos estáticos** (`/static/`) directamente.
- El “Data Lake” del trabajo es una **estructura de carpetas** montada al contenedor.

## Requisitos

- Docker Desktop (con `docker compose`)
- Python (solo si quieres correr local sin Docker)

## Instalación (Windows / PowerShell)

### 1) Clonar el repositorio

```powershell
cd "C:\Users\Acer\Desktop"
git clone https://github.com/Tornadusk/RetailStart.git
cd .\RetailStart
```

> Si ya tienes la carpeta descargada, solo entra a la raíz del proyecto:
>
> `cd "C:\ruta\a\RetailStart"`

### 2) Crear el archivo `.env`

```powershell
Copy-Item .\backend\.env.example .\backend\.env
```

### 3) Levantar con Docker (recomendado)

```powershell
docker compose up --build
```

Abrir en el navegador:

- **App**: `http://localhost:8080/`
- **Admin Django**: `http://localhost:8080/admin/`

## Estructura clave

- `backend/`: proyecto Django
- `nginx/`: configuración del reverse proxy y estáticos
- `data_sources/`: datos “sueltos” simulando orígenes en carpetas distintas (entrada del **ELT**). **Sí se versionan** en Git los CSV/JSON/XML de ejemplo del repo (no están en `.gitignore`).
- `data_lake/raw/`: landing zone única del lago (CSV/JSON/XML/TXT; lo rellena `run_elt_ingest` y/o manual)
- `data_lake/processed/`: datos preprocesados (salida del ETL batch)
- `data_lake/processed/evidence/`: gráficos de evidencia (análisis)

**Git:** en `.gitignore` se excluyen los artefactos bajo `data_lake/raw/**` y `data_lake/processed/**` (CSV/JSON/XML/TXT en raw, CSV en processed, PNG en evidence) para no subir datos generados; se vuelven a crear con los pasos de **Actividad 2**. Las carpetas pueden llevar `.gitkeep` para mantener la estructura.

## Árbol del proyecto (tree)

```
RetailStart/
├─ backend/
│  ├─ retailstart/                # settings/urls/wsgi del proyecto Django
│  ├─ core/                       # app Django (ETL + DW + vistas)
│  │  ├─ etl/
│  │  │  └─ ingest_transform.py   # lee raw → limpia/unifica → escribe processed
│  │  ├─ management/commands/
│  │  │  ├─ run_elt_ingest.py      # comando: python manage.py run_elt_ingest (ELT: E+L → raw)
│  │  │  ├─ run_etl.py            # comando: python manage.py run_etl
│  │  │  ├─ load_dw.py            # comando: python manage.py load_dw
│  │  │  └─ analyze_dw.py         # comando: python manage.py analyze_dw
│  │  └─ models.py                # modelo estrella: dimensiones + hechos
│  ├─ templates/core/home.html    # HTML (separado del CSS/JS)
│  └─ static/                     # CSS y JS separados
│     ├─ css/main.css
│     └─ js/main.js
├─ data_sources/                  # orígenes dispersos (ERP, CRM, POS, etc.)
├─ data_lake/
│  ├─ raw/                        # consolidado desde data_sources u origen único (anexo)
│  └─ processed/                  # salidas del ETL + evidence/
├─ nginx/default.conf             # reverse proxy + servir /static/
├─ docker-compose.yml             # orquestación (db + backend + nginx)
├─ requirements.txt               # dependencias Python
└─ README.md
```

## Flujo “quién llama a quién”

### Flujo web (navegador → app)

1) **Navegador** → `http://localhost:8080/`
2) **Nginx** (`nginx/default.conf`) recibe la request:
   - Si es `/static/...` → sirve desde el volumen `staticfiles`
   - Si es `/` o `/admin/` → hace proxy a `backend:8000`
3) **Backend** (Gunicorn + Django) resuelve rutas en `backend/retailstart/urls.py` y renderiza templates.

### Flujo de datos (Actividad 2)

0) `python manage.py run_elt_ingest` (**ELT**: Extract + Load al lago)
   - Copia archivos desde varias carpetas bajo `data_sources/` hacia `data_lake/raw/`
   - **Sin transformar**: solo lleva todo al landing zone del data lake

1) `python manage.py run_etl`
   - Ejecuta `core.management.commands.run_etl`
   - Llama a `core.etl.ingest_transform.run_pipeline`
   - Lee fuentes desde `data_lake/raw/` y escribe CSV “limpios” en `data_lake/processed/`

2) `python manage.py load_dw`
   - Ejecuta `core.management.commands.load_dw`
   - Lee los **últimos** CSV procesados (por timestamp) en `data_lake/processed/`
   - Carga el modelo estrella en Postgres:
     - Dimensiones: `DimCliente`, `DimProducto`, `DimTiempo`, `DimCanal`
     - Hechos: `FactVentas`

3) `python manage.py analyze_dw`
   - Ejecuta `core.management.commands.analyze_dw`
   - Consulta `FactVentas` (agregaciones) y guarda PNG en `data_lake/processed/evidence/`

## Variables de entorno

1) Copia el ejemplo y crea el archivo real:

```powershell
cd "C:\ruta\a\RetailStart"
Copy-Item .\backend\.env.example .\backend\.env
```

2) Edita `backend/.env` si quieres cambiar usuario/clave de Postgres o `DJANGO_SECRET_KEY`.

## Levantar con Docker (recomendado)

Desde la raíz del proyecto:

```powershell
cd "C:\ruta\a\RetailStart"
docker compose up --build
```

Abrir en el navegador:

- **App**: `http://localhost:8080/`
- **Admin Django**: `http://localhost:8080/admin/`

Nota: este proyecto **no se usa en `http://127.0.0.1:8000/`** cuando estás en Docker; ese puerto es típico de `runserver` local.

### Cambios en código o plantillas (sin `docker compose build`)

`docker-compose.yml` monta `./backend` en el contenedor, así que **no hace falta reconstruir la imagen** cuando editas Python, HTML, CSS o JS en `backend/`.

| Qué cambiaste | Qué hacer |
|---------------|-----------|
| Archivos **`.py`** (vistas, comandos, ETL) | Gunicorn usa `--reload`: suele aplicarse solo. Si no ves el cambio, reinicia el backend. |
| Plantillas **`.html`** en `backend/templates/` | Gunicorn **no** recarga HTML automáticamente. Ejecuta: `docker compose restart backend` y recarga el navegador (`Ctrl+Shift+R`). |
| **CSS/JS** en `backend/static/` | Tras reiniciar (si hace falta), fuerza recarga en el navegador; las URLs llevan `?v=` para romper caché. |
| **`requirements.txt`** o **`Dockerfile`** | Sí necesitas: `docker compose up --build` |

```powershell
docker compose restart backend
```

Luego abre de nuevo `http://localhost:8080/flow/` (o `/analytics/`) con recarga forzada.

Para bajar contenedores:

```powershell
docker compose down
```

Para borrar también la data persistida de Postgres:

```powershell
docker compose down -v
```

## Cargas incrementales (Día 1 → Día 2)

Para la evidencia de la rúbrica (raw → processed → DW sin borrar histórico), ver **`data_sources/README.md`** y la sección **Pipeline y comandos Docker** en la web (`/flow/`, `/analytics/`).

Resumen:

```powershell
docker compose exec backend python manage.py run_incremental_day --day dia_1 --ingest-date 2026-04-01
docker compose exec backend python manage.py audit_pipeline
docker compose exec backend python manage.py run_incremental_day --day dia_2 --ingest-date 2026-04-02
docker compose exec backend python manage.py audit_pipeline
```

## Actividad 2 (ETL + DW + Visualización)

La actividad pide simular un flujo moderno:

- **ELT (fase ingest)**: reunionar datos desde carpetas/orígenes dispersos (`data_sources/`) en el data lake (`data_lake/raw/`) sin cambiar el contenido
- **Ingesta / ETL**: leer desde `data_lake/raw/` y procesar batch (pandas) hacia `data_lake/processed/`
- **Procesamiento batch**: limpieza/unificación y salida a `data_lake/processed/`
- **Data Warehouse**: cargar a Postgres un **modelo estrella** (dimensiones + hechos)
- **Consumo**: responder preguntas con agregaciones y gráficos

### 0) ELT: llevar datos sueltos al Data Lake (`raw/`)

Útil cuando los archivos del anexo están repartidos en varias carpetas (simula CRM, ERP, POS, logs, etc.).  
**En `data_lake/raw/` los nombres llevan sufijo `_YYYYMMDD`** (fecha de ingesta; por defecto la del sistema; se puede fijar con `--ingest-date`).

```powershell
cd "v:\Base de datos\Almacenamientos de datos\RetailStart"
docker compose exec backend python manage.py run_elt_ingest
```

Sin Docker (desde `backend/`, rutas relativas al repo):

```powershell
python manage.py run_elt_ingest --sources-root "..\data_sources" --lake-root "..\data_lake"
```

Opcional: `python manage.py run_elt_ingest --ingest-date 2026-05-07` (también admite `YYYYMMDD`).

### 1) Ejecutar el ETL (batch)

Esto genera datasets “limpios” en `data_lake/processed/`.

```powershell
cd "C:\ruta\a\RetailStart"
docker compose exec backend python manage.py run_etl
```

### 2) Cargar el Data Warehouse (modelo estrella)

Carga en Postgres:
- `DimCliente`, `DimProducto`, `DimCanal`
- **`DimTiempo`**: calendario **pre-generado** (por defecto años **2020–2030**, un registro por día) con `id_tiempo` = entero **AAAAMMDD**, `nombre_dia` (Lunes…), `nombre_mes`, trimestre y `es_fin_semana`. No se alimenta desde las fuentes CSV; sirve para cortes por día/semana/mes/año y consultas tipo BI.
- `FactVentas` enlaza a `DimTiempo` mediante la FK `fecha` (internamente `fecha_id` = mismo valor que `DimTiempo.id_tiempo`).

```powershell
cd "C:\ruta\a\RetailStart"
docker compose exec backend python manage.py load_dw
```

Para ampliar el rango del calendario si tus ventas tienen años fuera del intervalo:

```powershell
docker compose exec backend python manage.py load_dw --calendar-from 2018 --calendar-to 2035
```

Ejemplo de consulta (Power BI/SQL client) equivalente a *“¿cómo nos fue todos los lunes de enero de 2026?”* usando tablas físicas Django (`core_factventas` / `core_dimtiempo`):

```sql
SELECT SUM(f.monto) AS total_monto
FROM core_factventas f
JOIN core_dimtiempo t ON f.fecha_id = t.id_tiempo
WHERE t.nombre_dia = 'Lunes'
  AND t.nombre_mes = 'Enero'
  AND t.anio = 2026;
```

### 3) Generar evidencia (gráficos)

Crea gráficos PNG en `data_lake/processed/evidence/`:
- mejores clientes
- ventas por canal
- productos con más ventas

```powershell
cd "C:\ruta\a\RetailStart"
docker compose exec backend python manage.py analyze_dw
```

### Preguntas que responde (Actividad 2)

- **¿Quiénes son los mejores clientes?**: `top_clientes.png`
- **¿Qué canal vende más?**: `ventas_por_canal.png`
- **¿Qué producto tiene más ventas?**: `top_productos.png`

## ¿Para qué sirve `nginx/`?

Nginx es el “front” del stack en Docker:

- Expone el puerto del host (`8080`) y recibe las peticiones HTTP.
- Redirige las peticiones dinámicas a Django (`backend:8000`).
- Sirve `/static/` directamente desde el volumen `staticfiles` (lo que Django genera con `collectstatic`).

Esto es un patrón común para despliegue y cumple con “front y backend por docker” sin necesitar React/Vue.

## Correr sin Docker (opcional)

```powershell
cd "C:\ruta\a\RetailStart"
python -m venv .venv
.\.venv\Scripts\python -m pip install -r .\requirements.txt
Copy-Item .\backend\.env.example .\backend\.env
cd .\backend
..\.\.venv\Scripts\python manage.py migrate
..\.\.venv\Scripts\python manage.py runserver
```

En este modo debes tener Postgres disponible y ajustar `backend/.env` (por defecto apunta a `db` que es el servicio del compose).

Si quieres usar **Postgres via Docker** pero correr Django local, levanta solo la BD y apunta a `localhost`:

```powershell
cd "C:\ruta\a\RetailStart"
docker compose up -d db
```

En `backend/.env` deja:

- `POSTGRES_HOST=localhost`
- `POSTGRES_PORT=5432`
