from __future__ import annotations

from pathlib import Path
from typing import Any

from django.db.models import Sum
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from core.models import DimCanal, DimCliente, DimProducto, DimTiempo, FactVentas


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "core/home.html")


def evidence(request: HttpRequest) -> HttpResponse:
    processed_dir = Path("/data_lake/processed")
    evidence_dir = processed_dir / "evidence"

    images: list[dict[str, str]] = []
    if evidence_dir.exists():
        # Deduplicar por nombre de archivo: si existen copias antiguas, quedarse con el PNG más reciente.
        latest_png: dict[str, Path] = {}
        for p in evidence_dir.glob("*.png"):
            prev = latest_png.get(p.name)
            if prev is None or p.stat().st_mtime >= prev.stat().st_mtime:
                latest_png[p.name] = p

        for name in sorted(latest_png.keys()):
            p = latest_png[name]
            v = int(p.stat().st_mtime)
            images.append({"name": name, "url": f"/evidence/file/{name}?v={v}"})

    file_rows: list[dict[str, str]] = []
    if processed_dir.exists():
        # Solo CSV en la raíz de processed (no mezclar con evidence/).
        for p in sorted(processed_dir.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)[:40]:
            if p.parent != processed_dir:
                continue
            st = p.stat()
            file_rows.append(
                {
                    "name": p.name,
                    "url": f"/evidence/file/{p.name}",
                    "size_kb": f"{max(1, int(st.st_size / 1024))} KB",
                }
            )

    latest_processed = file_rows[0]["name"] if file_rows else None
    latest_chart = images[-1]["name"] if images else None

    dw_counts = {
        "dim_cliente": DimCliente.objects.count(),
        "dim_producto": DimProducto.objects.count(),
        "dim_tiempo": DimTiempo.objects.count(),
        "dim_canal": DimCanal.objects.count(),
        "fact_ventas": FactVentas.objects.count(),
    }

    return render(
        request,
        "core/evidence.html",
        {
            "images": images,
            "files": file_rows,
            "latest_processed": latest_processed,
            "latest_chart": latest_chart,
            "dw_counts": dw_counts,
        },
    )


def _count_files_recursive(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file())


def flow(request: HttpRequest) -> HttpResponse:
    raw_dir = Path("/data_lake/raw")
    sources_dir = Path("/data_sources")
    processed_dir = Path("/data_lake/processed")
    evidence_dir = processed_dir / "evidence"

    scattered_count = _count_files_recursive(sources_dir)
    raw_files = sorted(raw_dir.glob("*")) if raw_dir.exists() else []
    raw_summary: dict[str, int] = {"csv": 0, "json": 0, "xml": 0, "txt": 0, "otros": 0}
    for p in raw_files:
        ext = p.suffix.lower().lstrip(".")
        if ext in raw_summary:
            raw_summary[ext] += 1
        else:
            raw_summary["otros"] += 1

    processed_csv_count = len(list(processed_dir.glob("*.csv"))) if processed_dir.exists() else 0
    evidence_png_count = len(list(evidence_dir.glob("*.png"))) if evidence_dir.exists() else 0
    dw_fact_count = FactVentas.objects.count()

    dw_counts = {
        "dim_cliente": DimCliente.objects.count(),
        "dim_producto": DimProducto.objects.count(),
        "dim_tiempo": DimTiempo.objects.count(),
        "dim_canal": DimCanal.objects.count(),
        "fact_ventas": FactVentas.objects.count(),
    }

    raw_total = sum(raw_summary.values())
    steps: list[dict[str, Any]] = [
        {
            "name": "Origen",
            "desc": "Fuentes del anexo repartidas en varias carpetas (`/data_sources/`) que simulan CRM, ERP, POS, etc.",
            "tech": ["CSV", "JSON", "XML", "TXT"],
            "status_ok": scattered_count > 0 or raw_total > 0,
            "details": (
                f"data_sources: {scattered_count} archivos (dispersos) · "
                f"raw: {raw_total} (csv {raw_summary['csv']}, json {raw_summary['json']}, "
                f"xml {raw_summary['xml']}, txt {raw_summary['txt']})"
            ),
        },
        {
            "name": "Ingesta",
            "desc": "ELT (E+L): copiar todo al landing `raw/` sin transformar. Luego ETL batch con pandas.",
            "tech": ["ELT: run_elt_ingest", "ETL: run_etl", "pandas"],
            "status_ok": raw_total > 0,
            "details": (
                "1) python manage.py run_elt_ingest → consolida `data_sources/` en `data_lake/raw/`. "
                "2) python manage.py run_etl → escribe `data_lake/processed/`."
            ),
        },
        {
            "name": "Almacenamiento",
            "desc": "Data Lake (raw/processed) + Data Warehouse (Postgres).",
            "tech": ["Data Lake (FS)", "Postgres"],
            "status_ok": processed_csv_count > 0 or dw_counts["fact_ventas"] > 0,
            "details": f"processed: {processed_csv_count} CSV | DW FactVentas: {dw_counts['fact_ventas']}",
        },
        {
            "name": "Procesamiento",
            "desc": "Transformación (batch) + carga del modelo estrella en el DW.",
            "tech": ["Scripts Python", "Django commands"],
            "status_ok": processed_csv_count > 0 and dw_counts["fact_ventas"] > 0,
            "details": "Comandos: run_etl → load_dw",
        },
        {
            "name": "Consumo",
            "desc": "Dashboard/consultas: PNG + KPIs (/evidence/) y tablas SQL (/analytics/).",
            "tech": ["Django", "Nginx", "matplotlib", "SQL/JDBC-like (ORM)"],
            "status_ok": evidence_png_count > 0 and dw_fact_count > 0,
            "details": f"PNG: {evidence_png_count} (ver /evidence/) · DW cargado: FactVentas={dw_fact_count} (ver /analytics/)",
        },
    ]

    return render(
        request,
        "core/flow.html",
        {
            "steps": steps,
            "dw_counts": dw_counts,
        },
    )


def analytics(request: HttpRequest) -> HttpResponse:
    """
    Consumo tipo BI (tablas navegables) sobre el Data Warehouse (Postgres).

    Responde las preguntas típicas de la actividad:
    - mejores clientes
    - rendimiento por canal
    - productos líderes
    """

    top_clientes = (
        FactVentas.objects.values(
            "cliente__id_cliente",
            "cliente__nombre",
            "cliente__apellido",
            "cliente__segmento",
        )
        .annotate(total=Sum("monto"))
        .order_by("-total")[:15]
    )

    top_canales = (
        FactVentas.objects.values("canal__canal").annotate(total=Sum("monto")).order_by("-total")
    )

    top_productos = (
        FactVentas.objects.values(
            "producto__id_producto",
            "producto__nombre_producto",
            "producto__categoria",
        )
        .annotate(total=Sum("monto"))
        .order_by("-total")[:15]
    )

    # Evitar server-side cursors (iterator) en Postgres:
    # en algunos entornos el cursor puede invalidarse durante el render (InvalidCursorName).
    preview_rows = list(
        FactVentas.objects.select_related("cliente", "producto", "canal", "fecha").order_by(
            "-fecha__fecha_completa", "-id"
        )[:50]
    )

    preview = []
    for fv in preview_rows:
        preview.append(
            {
                "fecha": fv.fecha.fecha_completa.isoformat(),
                "id_cliente": fv.cliente.id_cliente,
                "cliente": f'{fv.cliente.nombre} {fv.cliente.apellido}',
                "segmento": fv.cliente.segmento,
                "canal": fv.canal.canal,
                "id_producto": "" if fv.producto is None else fv.producto.id_producto,
                "producto": "" if fv.producto is None else fv.producto.nombre_producto,
                "cantidad": fv.cantidad,
                "monto": fv.monto,
            }
        )

    return render(
        request,
        "core/analytics.html",
        {
            "top_clientes": list(top_clientes),
            "top_canales": list(top_canales),
            "top_productos": list(top_productos),
            "preview": preview,
        },
    )


def evidence_file(request: HttpRequest, filename: str) -> FileResponse:
    processed_dir = Path("/data_lake/processed")
    evidence_dir = processed_dir / "evidence"

    safe_name = Path(filename).name
    candidate = evidence_dir / safe_name
    if not candidate.exists():
        candidate = processed_dir / safe_name

    if not candidate.exists() or not candidate.is_file():
        raise Http404("File not found")

    return FileResponse(candidate.open("rb"))
