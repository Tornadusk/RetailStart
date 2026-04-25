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
- `data_lake/raw/`: datos brutos (CSV/JSON/XML, etc.)
- `data_lake/processed/`: datos preprocesados antes de cargar a Postgres

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

Para bajar contenedores:

```powershell
docker compose down
```

Para borrar también la data persistida de Postgres:

```powershell
docker compose down -v
```

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
