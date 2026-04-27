from __future__ import annotations

from pathlib import Path
from typing import Any

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
        for p in sorted(evidence_dir.glob("*.png")):
            images.append({"name": p.name, "url": f"/evidence/file/{p.name}"})

    file_rows: list[dict[str, str]] = []
    if processed_dir.exists():
        for p in sorted(processed_dir.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)[:40]:
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


def flow(request: HttpRequest) -> HttpResponse:
    raw_dir = Path("/data_lake/raw")
    processed_dir = Path("/data_lake/processed")
    evidence_dir = processed_dir / "evidence"

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

    dw_counts = {
        "dim_cliente": DimCliente.objects.count(),
        "dim_producto": DimProducto.objects.count(),
        "dim_tiempo": DimTiempo.objects.count(),
        "dim_canal": DimCanal.objects.count(),
        "fact_ventas": FactVentas.objects.count(),
    }

    steps: list[dict[str, Any]] = [
        {
            "name": "Origen",
            "desc": "Fuentes simuladas (anexo) en archivos planos.",
            "tech": ["CSV", "JSON", "XML", "TXT"],
            "status_ok": sum(raw_summary.values()) > 0,
            "details": f"raw: {sum(raw_summary.values())} archivos (csv {raw_summary['csv']}, json {raw_summary['json']}, xml {raw_summary['xml']}, txt {raw_summary['txt']})",
        },
        {
            "name": "Ingesta",
            "desc": "Lectura desde Data Lake (carpetas) hacia pandas.",
            "tech": ["Python", "pandas"],
            "status_ok": True,
            "details": "Comando: python manage.py run_etl",
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
            "desc": "ETL/ELT: limpieza, unificación omnicanal y modelo estrella.",
            "tech": ["Scripts Python", "Django commands"],
            "status_ok": processed_csv_count > 0 and dw_counts["fact_ventas"] > 0,
            "details": "Comandos: run_etl → load_dw",
        },
        {
            "name": "Consumo",
            "desc": "Dashboard/consultas: gráficos y descargas desde la web.",
            "tech": ["Django", "Nginx", "matplotlib"],
            "status_ok": evidence_png_count > 0,
            "details": f"evidence: {evidence_png_count} PNG (ver /evidence/)",
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
