# RetailStart (Django + Postgres + Nginx + Docker)

Este proyecto levanta una web en **Django** dentro de Docker, usando **Postgres** (solo para Django) y **Nginx** como “front”:

- Nginx funciona como **reverse proxy** hacia Django/Gunicorn.
- Nginx sirve los **archivos estáticos** (`/static/`) directamente.
- El “Data Lake” del trabajo es una **estructura de carpetas** montada al contenedor.

## Requisitos

- Docker Desktop (con `docker compose`)
- Python (solo si quieres correr local sin Docker)

## Estructura clave

- `backend/`: proyecto Django
- `nginx/`: configuración del reverse proxy y estáticos
- `data_lake/raw/`: datos brutos (CSV/JSON/XML/TXT, etc.)
- `data_lake/processed/`: datos preprocesados (salida del ETL)
- `data_lake/processed/evidence/`: gráficos de evidencia (análisis)

## Árbol del proyecto (tree)

```
RetailStart/
├─ backend/
│  ├─ retailstart/                # settings/urls/wsgi del proyecto Django
│  ├─ core/                       # app Django (ETL + DW + vistas)
│  │  ├─ etl/
│  │  │  └─ ingest_transform.py   # lee raw → limpia/unifica → escribe processed
│  │  ├─ management/commands/
│  │  │  ├─ run_etl.py            # comando: python manage.py run_etl
│  │  │  ├─ load_dw.py            # comando: python manage.py load_dw
│  │  │  └─ analyze_dw.py         # comando: python manage.py analyze_dw
│  │  └─ models.py                # modelo estrella: dimensiones + hechos
│  ├─ templates/core/home.html    # HTML (separado del CSS/JS)
│  └─ static/                     # CSS y JS separados
│     ├─ css/main.css
│     └─ js/main.js
├─ data_lake/
│  ├─ raw/                        # fuentes originales (anexo)
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
cd "v:\Base de datos\Almacenamientos de datos\RetailStart"
Copy-Item .\backend\.env.example .\backend\.env
```

2) Edita `backend/.env` si quieres cambiar usuario/clave de Postgres o `DJANGO_SECRET_KEY`.

## Levantar con Docker (recomendado)

Desde la raíz del proyecto:

```powershell
cd "v:\Base de datos\Almacenamientos de datos\RetailStart"
docker compose up --build
```

Abrir en el navegador:

- **App**: `http://localhost:8080/`
- **Admin Django**: `http://localhost:8080/admin/`

Nota: este proyecto **no se usa en `http://127.0.0.1:8000/`** cuando estás en Docker; ese puerto es típico de `runserver` local.

Para bajar contenedores:

```powershell
docker compose down
```

Para borrar también la data persistida de Postgres:

```powershell
docker compose down -v
```

## Actividad 2 (ETL + DW + Visualización)

La actividad pide simular un flujo moderno:

- **Ingesta**: leer fuentes heterogéneas (CSV/JSON/XML/TXT) desde `data_lake/raw/`
- **Procesamiento batch**: limpieza/unificación y salida a `data_lake/processed/`
- **Data Warehouse**: cargar a Postgres un **modelo estrella** (dimensiones + hechos)
- **Consumo**: responder preguntas con agregaciones y gráficos

### 1) Ejecutar el ETL (batch)

Esto genera datasets “limpios” en `data_lake/processed/`.

```powershell
cd "v:\Base de datos\Almacenamientos de datos\RetailStart"
docker compose exec backend python manage.py run_etl
```

### 2) Cargar el Data Warehouse (modelo estrella)

Carga en Postgres:
- `DimCliente`, `DimProducto`, `DimTiempo`, `DimCanal`
- `FactVentas`

```powershell
cd "v:\Base de datos\Almacenamientos de datos\RetailStart"
docker compose exec backend python manage.py load_dw
```

### 3) Generar evidencia (gráficos)

Crea gráficos PNG en `data_lake/processed/evidence/`:
- mejores clientes
- ventas por canal
- productos con más ventas

```powershell
cd "v:\Base de datos\Almacenamientos de datos\RetailStart"
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
cd "v:\Base de datos\Almacenamientos de datos\RetailStart"
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
cd "v:\Base de datos\Almacenamientos de datos\RetailStart"
docker compose up -d db
```

En `backend/.env` deja:

- `POSTGRES_HOST=localhost`
- `POSTGRES_PORT=5432`
