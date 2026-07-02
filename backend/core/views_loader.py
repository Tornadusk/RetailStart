from __future__ import annotations

"""
Cargador Masivo Web — segunda opción para ingestar datos sin Docker CLI.

Permite subir CSVs directamente desde el navegador, ejecutando el pipeline
ELT → ETL → DW de forma transparente.
"""

import json
import shutil
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from core.models import DimCanal, DimCliente, DimProducto, DimTiempo, DimTienda, FactVentas

# Docker paths (inside container)
_LAKE_ROOT = Path("/data_lake")
_SOURCES_ROOT = Path("/data_sources")

# Required files for a full load
_REQUIRED_FILES = {"ventas_pos.csv", "ventas_online.csv", "clientes_crm.csv", "productos_erp.csv"}
_OPTIONAL_FILES = {
    "eventos_app.json", "logistica.xml", "logs_sistema.txt",
    "callcenter.csv", "redes_sociales.json", "proveedores.csv", "multimedia.csv",
}
_ALL_KNOWN_FILES = _REQUIRED_FILES | _OPTIONAL_FILES

# History file
_HISTORY_FILE = _LAKE_ROOT / "processed" / ".loader_history.json"


def _load_history() -> list[dict[str, Any]]:
    if _HISTORY_FILE.is_file():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_history(history: list[dict[str, Any]]) -> None:
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(history, indent=2, default=str), encoding="utf-8")


def _dw_counts() -> dict[str, int]:
    return {
        "dim_cliente": DimCliente.objects.count(),
        "dim_producto": DimProducto.objects.count(),
        "dim_tiempo": DimTiempo.objects.count(),
        "dim_canal": DimCanal.objects.count(),
        "dim_tienda": DimTienda.objects.count(),
        "fact_ventas": FactVentas.objects.count(),
    }


def loader(request: HttpRequest) -> HttpResponse:
    """Main loader page with upload form and history."""
    history = _load_history()
    counts = _dw_counts()
    
    # Get available commands with their help text
    from django.core.management import load_command_class
    cmds_dir = Path(__file__).parent / "management" / "commands"
    commands = []
    # Dictionary with detailed flow explanations (HTML)
    CMD_DETAILS = {
        "run_elt_ingest": (
            "<strong>Flujo ELT:</strong> <code class='text-mars-accent'>Origen &#8594; Raw</code><br><br>"
            "Toma los archivos fuentes dispersos en <code>/data_sources/</code> y los transfiere "
            "a la capa de aterrizaje <code>/data_lake/raw/</code>, añadiéndoles un sufijo de fecha."
        ),
        "run_etl": (
            "<strong>Flujo ETL:</strong> <code class='text-mars-accent'>Raw &#8594; Processed</code><br><br>"
            "Lee los archivos crudos de <code>/raw/</code>, los limpia y los anexa al archivo "
            "maestro consolidado en <code>/data_lake/processed/ventas_unificadas_maestro.csv</code>."
        ),
        "load_dw": (
            "<strong>Flujo DW:</strong> <code class='text-mars-accent'>Processed &#8594; Data Warehouse</code><br><br>"
            "Lee el archivo maestro y realiza una carga incremental en el modelo estrella de Postgres "
            "(Dimensiones y <code>FactVentas</code>)."
        ),
        "audit_pipeline": (
            "<strong>Auditoría:</strong> <code class='text-mars-accent'>Validación de Capas</code><br><br>"
            "Genera conteos de validación a lo largo de todo el pipeline: archivos en <code>raw</code>, "
            "filas en <code>processed</code> y registros en <code>Postgres</code> para generar evidencia."
        ),
        "run_incremental_day": (
            "<strong>Flujo Completo:</strong> <code class='text-mars-accent'>Origen &#8594; Raw &#8594; Processed &#8594; DW &#8594; Auditoría</code><br><br>"
            "Ejecuta en un solo paso todas las fases del pipeline para los datos de un día específico."
        ),
        "analyze_dw": (
            "<strong>Evidencia:</strong> <code class='text-mars-accent'>DW &#8594; Gráficos PNG</code><br><br>"
            "Realiza consultas SQL analíticas al Data Warehouse y genera gráficos de respaldo (PNG) "
            "en <code>/processed/evidence/</code>."
        ),
        "seed_week": (
            "<strong>Generador Automático:</strong> <code class='text-mars-accent'>Semana Completa</code><br><br>"
            "Crea archivos fuente ficticios y ejecuta el pipeline de forma continua para los 5 días "
            "de la semana, dejando el Data Warehouse listo con datos de muestra."
        ),
        "ingest_sales_batch": (
            "<strong>Ingesta de Lote Web:</strong> <code class='text-mars-accent'>Web &#8594; DW</code><br><br>"
            "Comando interno usado por la interfaz web para procesar el lote de archivos subidos y "
            "cargarlos al Data Warehouse."
        )
    }

    if cmds_dir.is_dir():
        for f in cmds_dir.glob("*.py"):
            if not f.name.startswith("_") and f.name != "__init__.py":
                cmd_name = f.stem
                try:
                    cmd_class = load_command_class("core", cmd_name)
                    cmd_help = cmd_class.help or "Sin descripción."
                except Exception:
                    cmd_help = "Comando de sistema."
                
                # Check if it's a seed_day command
                if cmd_name.startswith("seed_day_"):
                    day_num = cmd_name.split("_")[-1]
                    detailed_html = (
                        f"<strong>Generador Automático:</strong> <code class='text-mars-accent'>Día {day_num}</code><br><br>"
                        f"Ejecuta el flujo completo para el Día {day_num}. "
                        "Genera archivos fuente ficticios en <code>/data_sources/dia_{day_num}</code> y luego "
                        "corre el pipeline (ELT &#8594; ETL &#8594; DW)."
                    )
                else:
                    detailed_html = CMD_DETAILS.get(cmd_name, f"<strong>Descripción:</strong><br>{cmd_help}")

                commands.append({"name": cmd_name, "help": detailed_html})
    commands.sort(key=lambda x: x["name"])

    return render(request, "core/loader.html", {
        "history": history[-20:][::-1],  # last 20, newest first
        "dw_counts": counts,
        "today": date.today().isoformat(),
        "commands": commands,
    })


@require_http_methods(["POST"])
def loader_run_command(request: HttpRequest) -> JsonResponse:
    """Executes a management command and returns its output."""
    from django.core.management import call_command
    from io import StringIO
    
    command_name = request.POST.get("command", "").strip()
    if not command_name:
        return JsonResponse({"ok": False, "error": "No command specified."}, status=400)
    
    # Simple security check to avoid running non-whitelisted commands (only from core)
    cmds_dir = Path(__file__).parent / "management" / "commands"
    allowed_commands = [f.stem for f in cmds_dir.glob("*.py") if not f.name.startswith("_")]
    
    if command_name not in allowed_commands:
        return JsonResponse({"ok": False, "error": f"Comando no permitido: {command_name}"}, status=403)
        
    out = StringIO()
    err = StringIO()
    try:
        call_command(command_name, stdout=out, stderr=err)
        return JsonResponse({
            "ok": True, 
            "stdout": out.getvalue(),
            "stderr": err.getvalue()
        })
    except Exception as exc:
        return JsonResponse({
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "stdout": out.getvalue(),
            "stderr": err.getvalue()
        }, status=500)


@require_http_methods(["POST"])
def loader_process(request: HttpRequest) -> JsonResponse:
    """Process uploaded CSV files through the full pipeline."""
    from django.core.management import call_command
    from core.etl.elt_ingest import DEFAULT_SCATTERED_SOURCES, ingest_scattered_sources
    from core.etl.ingest_transform import run_pipeline

    ingest_date_str = request.POST.get("ingest_date", "").strip()
    batch_name = request.POST.get("batch_name", "").strip() or "web_upload"

    # Parse date
    try:
        if ingest_date_str:
            parts = ingest_date_str.split("-")
            ingest_day = date(int(parts[0]), int(parts[1]), int(parts[2]))
        else:
            ingest_day = date.today()
    except (ValueError, IndexError):
        return JsonResponse({"ok": False, "error": "Fecha inválida. Use formato YYYY-MM-DD."}, status=400)

    # Create temp staging directory
    staging_dir = _LAKE_ROOT / ".web_uploads" / f"{batch_name}_{ingest_day:%Y%m%d}"
    staging_dir.mkdir(parents=True, exist_ok=True)

    # Subdirectory structure matching what ingest_scattered_sources expects
    subdirs = {
        "ventas_pos.csv": "sistemas_legacy/pos",
        "ventas_online.csv": "marketplace",
        "clientes_crm.csv": "crm_export",
        "productos_erp.csv": "erp_snapshot",
        "eventos_app.json": "mobile_analytics",
        "logistica.xml": "sistemas_legacy/proveedor_logistica",
        "logs_sistema.txt": "infra_logs",
        "callcenter.csv": "crm_export",
        "redes_sociales.json": "marketing_analytics",
        "proveedores.csv": "erp_snapshot",
        "multimedia.csv": "catalogo_multimedia",
    }

    uploaded_names: list[str] = []
    errors: list[str] = []

    # Save uploaded files
    for f in request.FILES.getlist("files"):
        fname = f.name
        if fname not in _ALL_KNOWN_FILES:
            errors.append(f"Archivo no reconocido: {fname}")
            continue

        subdir = subdirs.get(fname, "")
        target_dir = staging_dir / subdir if subdir else staging_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / fname

        with open(target_path, "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        uploaded_names.append(fname)

    # Check required files
    missing = _REQUIRED_FILES - set(uploaded_names)
    if missing:
        # Try to find them in existing day sources
        for mf in list(missing):
            subdir = subdirs.get(mf, "")
            target_dir = staging_dir / subdir if subdir else staging_dir
            target_path = target_dir / mf
            if target_path.is_file():
                missing.discard(mf)

    if missing:
        return JsonResponse({
            "ok": False,
            "error": f"Faltan archivos obligatorios: {', '.join(sorted(missing))}",
            "uploaded": uploaded_names,
        }, status=400)

    # Create optional file stubs if missing (so ingest doesn't fail)
    _create_optional_stubs(staging_dir, subdirs, uploaded_names)

    # Run pipeline
    log_lines: list[str] = []
    counts_before = _dw_counts()

    try:
        # 1) ELT → raw/
        lake_raw = _LAKE_ROOT / "raw"
        written = ingest_scattered_sources(
            staging_dir, lake_raw, DEFAULT_SCATTERED_SOURCES, ingest_day=ingest_day,
        )
        log_lines.append(f"[1/3] ELT: {len(written)} archivos → raw/")

        # 2) ETL → processed/ + maestro
        outputs = run_pipeline(_LAKE_ROOT, append_master=True, ingest_day=ingest_day)
        log_lines.append(f"[2/3] ETL: {len(outputs)} salidas → processed/")

        # 3) DW incremental
        call_command(
            "load_dw",
            processed_dir=str(_LAKE_ROOT / "processed"),
            incremental=True,
            ventas_file="maestro",
        )
        log_lines.append("[3/3] load_dw --incremental ✓")

    except Exception as exc:
        log_lines.append(f"ERROR: {exc}")
        return JsonResponse({
            "ok": False,
            "error": str(exc),
            "log": log_lines,
            "traceback": traceback.format_exc(),
        }, status=500)

    counts_after = _dw_counts()

    # Save to history
    entry = {
        "timestamp": datetime.now().isoformat(),
        "batch_name": batch_name,
        "ingest_date": ingest_day.isoformat(),
        "files": uploaded_names,
        "counts_before": counts_before,
        "counts_after": counts_after,
        "new_facts": counts_after["fact_ventas"] - counts_before["fact_ventas"],
    }
    history = _load_history()
    history.append(entry)
    _save_history(history)

    return JsonResponse({
        "ok": True,
        "log": log_lines,
        "counts_before": counts_before,
        "counts_after": counts_after,
        "new_facts": entry["new_facts"],
        "batch_name": batch_name,
    })


def _create_optional_stubs(staging_dir: Path, subdirs: dict, uploaded: list[str]) -> None:
    """Create minimal stub files for optional sources not uploaded."""
    stubs = {
        "eventos_app.json": "[]",
        "logistica.xml": "<pedidos></pedidos>",
        "logs_sistema.txt": "",
        "callcenter.csv": "id_llamada,id_cliente,fecha,motivo,duracion",
        "redes_sociales.json": "[]",
        "proveedores.csv": "id_proveedor,nombre,producto,precio",
        "multimedia.csv": "id_producto,tipo,archivo",
    }
    for fname, content in stubs.items():
        if fname in uploaded:
            continue
        subdir = subdirs.get(fname, "")
        target_dir = staging_dir / subdir if subdir else staging_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / fname
        if not target_path.is_file():
            target_path.write_text(content + "\n", encoding="utf-8")
