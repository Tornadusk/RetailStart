from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from django.db.models import Count, Max, Min, QuerySet, Sum
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from core.etl.elt_ingest import DEFAULT_SCATTERED_SOURCES
from core.models import DimCanal, DimCliente, DimProducto, DimTiempo, FactVentas

# Etiquetas para la tabla de ingesta → raw (alineado con DEFAULT_SCATTERED_SOURCES en elt_ingest.py).
_LAKE_SOURCE_ROLE: dict[str, str] = {
    "ventas_pos.csv": "POS (tiendas)",
    "ventas_online.csv": "E-commerce / marketplace",
    "clientes_crm.csv": "CRM — clientes",
    "productos_erp.csv": "ERP — productos",
    "eventos_app.json": "App — eventos (opcional)",
    "logistica.xml": "Logística — pedidos (opcional)",
    "logs_sistema.txt": "Infra — logs (opcional)",
}


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


DIAS_SEMANA_CHOICES: tuple[tuple[str, str], ...] = (
    ("", "Todos"),
    ("Lunes", "Lunes"),
    ("Martes", "Martes"),
    ("Miércoles", "Miércoles"),
    ("Jueves", "Jueves"),
    ("Viernes", "Viernes"),
    ("Sábado", "Sábado"),
    ("Domingo", "Domingo"),
)

_ANALYTICS_FILTROS_ANCHOR = "#segmentar-ventas"


def _parse_optional_year(val: str | None) -> int | None:
    if val is None or not str(val).strip():
        return None
    try:
        y = int(val)
    except ValueError:
        return None
    return y if 1990 <= y <= 2100 else None


def _parse_optional_month(val: str | None) -> int | None:
    if val is None or not str(val).strip():
        return None
    try:
        m = int(val)
    except ValueError:
        return None
    return m if 1 <= m <= 12 else None


def _filter_fact_qs(qs: QuerySet, *, y: int | None, m: int | None, dia: str) -> QuerySet:
    if y is not None:
        qs = qs.filter(fecha__anio=y)
    if m is not None:
        qs = qs.filter(fecha__mes=m)
    if dia:
        qs = qs.filter(fecha__nombre_dia=dia)
    return qs


def _order_prefix(direction: str | None) -> str:
    return "-" if (direction or "asc").lower() == "desc" else ""


def _analytics_filter_qs(params: dict[str, Any]) -> str:
    """Querystring solo con filtros de tiempo (sin parámetros de orden)."""
    clean = {k: v for k, v in params.items() if v is not None and str(v) != ""}
    base = "?" + urlencode(clean) if clean else "?"
    return base + _ANALYTICS_FILTROS_ANCHOR


def _toggle_sort_href(request: HttpRequest, group: str, field: str, dir_key: str) -> str:
    q = request.GET.copy()
    prev = q.get(group)
    cur_dir = (q.get(dir_key) or "asc").lower()
    if prev == field:
        q[dir_key] = "desc" if cur_dir == "asc" else "asc"
    else:
        q[group] = field
        q[dir_key] = "asc"
    return "?" + q.urlencode()


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

    lake_route_rows: list[dict[str, str]] = []
    for sf in DEFAULT_SCATTERED_SOURCES:
        p = Path(sf.lake_raw_name)
        dated_pattern = f"{p.stem}_YYYYMMDD{p.suffix}"
        lake_route_rows.append(
            {
                "rol": _LAKE_SOURCE_ROLE.get(sf.lake_raw_name, sf.lake_raw_name),
                "sources_path": sf.relative_path.replace("\\", "/"),
                "raw_landing": dated_pattern,
                "formato": p.suffix.lstrip(".").upper() or "—",
            }
        )

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
            "desc": "Dashboard: PNG + KPIs (/evidence/) y tablas agregadas vía ORM (/analytics/).",
            "tech": ["Django ORM", "Nginx", "matplotlib"],
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
            "lake_route_rows": lake_route_rows,
        },
    )


def analytics(request: HttpRequest) -> HttpResponse:
    """
    Consumo tipo BI (tablas y KPIs) sobre el Data Warehouse en Postgres.

    Árbol de datos hasta esta vista::

        data_sources/  →  run_elt_ingest  →  data_lake/raw/
        data_lake/raw/ →  run_etl         →  data_lake/processed/*.csv
        processed/     →  load_dw         →  Postgres (FactVentas + dimensiones)
        Postgres       →  analyze_dw      →  processed/evidence/*.png  (no usado aquí directamente)

        Esta vista (core.views.analytics)
            └─ ORM sobre FactVentas + joins a DimTiempo / DimCliente / …
               · Querystring ?y=&m=&d= filtra hechos (`_filter_fact_qs`).
               · Agregaciones `.values(...).annotate(...)` = GROUP BY en SQL.
               · `preview` lista hechos con `select_related` (JOIN en una query).

    Parte 5 actividad: mejores clientes, canal, producto; más cortes por dimensión tiempo.
    """

    fy = _parse_optional_year(request.GET.get("y"))
    fm = _parse_optional_month(request.GET.get("m"))
    fd = (request.GET.get("d") or "").strip()

    facts_all = FactVentas.objects.all()
    agg_dates = facts_all.aggregate(
        dmin=Min("fecha__fecha_completa"),
        dmax=Max("fecha__fecha_completa"),
    )
    dw_total_unfiltered = facts_all.count()
    years_with_sales = sorted(
        {y for y in facts_all.values_list("fecha__anio", flat=True).distinct() if y is not None}
    )
    years_for_select = sorted(set(range(2000, 2036)) | set(years_with_sales))

    filter_parts: list[str] = []
    if fy is not None:
        filter_parts.append(f"Año {fy}")
    if fm is not None:
        filter_parts.append(f"Mes {fm:02d}")
    if fd:
        filter_parts.append(fd)
    filter_summary = " · ".join(filter_parts) if filter_parts else "Sin filtros (todos los hechos)"

    quick_time_links: list[dict[str, str]] = [{"label": "Quitar filtros", "href": "?" + _ANALYTICS_FILTROS_ANCHOR}]
    dmin, dmax = agg_dates["dmin"], agg_dates["dmax"]
    if dmin is not None and dmax is not None:
        y0, m0 = dmin.year, dmin.month
        y1 = dmax.year
        quick_time_links.extend(
            [
                {"label": f"Todo el año {y0}", "href": _analytics_filter_qs({"y": y0})},
                {"label": f"Todo el año {y1}", "href": _analytics_filter_qs({"y": y1})},
                {"label": "Solo lunes", "href": _analytics_filter_qs({"d": "Lunes"})},
                {"label": "Solo martes", "href": _analytics_filter_qs({"d": "Martes"})},
                {"label": "Solo miércoles", "href": _analytics_filter_qs({"d": "Miércoles"})},
                {
                    "label": f"Domingos de {m0:02d}/{y0}",
                    "href": _analytics_filter_qs({"y": y0, "m": m0, "d": "Domingo"}),
                },
                {
                    "label": f"Todos los meses de {y0} (sin filtrar día)",
                    "href": _analytics_filter_qs({"y": y0}),
                },
            ]
        )

    qs = _filter_fact_qs(facts_all, y=fy, m=fm, dia=fd)

    # Modelo estrella: qs es FactVentas; cada .values("fecha__…") proyecta DimTiempo vía FK fecha_id.
    star_model = {
        "dim_cliente": DimCliente.objects.count(),
        "dim_producto": DimProducto.objects.count(),
        "dim_tiempo": DimTiempo.objects.count(),
        "dim_canal": DimCanal.objects.count(),
        "fact_ventas": FactVentas.objects.count(),
        "hechos_filtrados": qs.count(),
    }

    tiempo_ids_en_hechos = qs.values_list("fecha_id", flat=True).distinct()

    dim_ord = request.GET.get("dim_ord", "fecha") or "fecha"
    dim_field_map = {
        "fecha": "fecha_completa",
        "id": "id_tiempo",
        "dia": "nombre_dia",
        "anio": "anio",
    }
    ob_dim = dim_field_map.get(dim_ord, "fecha_completa")
    p_dim = _order_prefix(request.GET.get("dim_dir"))
    dim_tiempo_en_hechos = list(
        DimTiempo.objects.filter(pk__in=tiempo_ids_en_hechos).order_by(f"{p_dim}{ob_dim}")[:120]
    )

    dc_ord = request.GET.get("dc_ord", "fecha") or "fecha"
    dc_field_map = {
        "fecha": "fecha__fecha_completa",
        "id": "fecha__id_tiempo",
        "monto": "total_monto",
        "tx": "transacciones",
    }
    p_dc = _order_prefix(request.GET.get("dc_dir"))
    ob_dc = dc_field_map.get(dc_ord, "fecha__fecha_completa")

    ventas_por_dia_civil = list(
        qs.values("fecha__id_tiempo", "fecha__fecha_completa", "fecha__nombre_dia")
        .annotate(total_monto=Sum("monto"), transacciones=Count("id"))
        .order_by(f"{p_dc}{ob_dc}")
    )

    sem_ord = request.GET.get("sem_ord", "dia") or "dia"
    sem_map = {"dia": "fecha__dia_semana", "monto": "total_monto", "tx": "transacciones"}
    p_sem = _order_prefix(request.GET.get("sem_dir"))
    ob_sem = sem_map.get(sem_ord, "fecha__dia_semana")

    ventas_por_dia_semana = list(
        qs.values("fecha__nombre_dia", "fecha__dia_semana")
        .annotate(total_monto=Sum("monto"), transacciones=Count("id"))
        .order_by(f"{p_sem}{ob_sem}")
    )

    mes_ord = request.GET.get("mes_ord", "periodo") or "periodo"
    p_mes = _order_prefix(request.GET.get("mes_dir"))
    if mes_ord == "periodo":
        ventas_por_mes_anio = list(
            qs.values("fecha__anio", "fecha__mes", "fecha__nombre_mes")
            .annotate(total_monto=Sum("monto"), transacciones=Count("id"))
            .order_by(f"{p_mes}fecha__anio", f"{p_mes}fecha__mes")
        )
    else:
        ob_m = "total_monto" if mes_ord == "monto" else "transacciones"
        ventas_por_mes_anio = list(
            qs.values("fecha__anio", "fecha__mes", "fecha__nombre_mes")
            .annotate(total_monto=Sum("monto"), transacciones=Count("id"))
            .order_by(f"{p_mes}{ob_m}")
        )

    ej_orm_lunes_enero_2026 = (
        qs.filter(
            fecha__nombre_dia="Lunes",
            fecha__nombre_mes="Enero",
            fecha__anio=2026,
        ).aggregate(total=Sum("monto"))["total"]
        or 0
    )

    top_clientes = (
        qs.values(
            "cliente__id_cliente",
            "cliente__nombre",
            "cliente__apellido",
            "cliente__segmento",
        )
        .annotate(total=Sum("monto"))
        .order_by("-total")[:15]
    )

    top_canales = qs.values("canal__canal").annotate(total=Sum("monto")).order_by("-total")

    top_productos = (
        qs.values(
            "producto__id_producto",
            "producto__nombre_producto",
            "producto__categoria",
        )
        .annotate(total=Sum("monto"))
        .order_by("-total")[:15]
    )

    preview_rows = list(
        qs.select_related("cliente", "producto", "canal", "fecha").order_by(
            "-fecha__fecha_completa", "-id"
        )[:50]
    )

    preview = []
    for fv in preview_rows:
        preview.append(
            {
                "id_tiempo": fv.fecha.id_tiempo,
                "fecha": fv.fecha.fecha_completa.isoformat(),
                "dia": fv.fecha.dia_mes,
                "mes": fv.fecha.mes,
                "anio": fv.fecha.anio,
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

    sort_href = {
        "dim_fecha": _toggle_sort_href(request, "dim_ord", "fecha", "dim_dir"),
        "dim_id": _toggle_sort_href(request, "dim_ord", "id", "dim_dir"),
        "dim_dia": _toggle_sort_href(request, "dim_ord", "dia", "dim_dir"),
        "dim_anio": _toggle_sort_href(request, "dim_ord", "anio", "dim_dir"),
        "dc_fecha": _toggle_sort_href(request, "dc_ord", "fecha", "dc_dir"),
        "dc_id": _toggle_sort_href(request, "dc_ord", "id", "dc_dir"),
        "dc_monto": _toggle_sort_href(request, "dc_ord", "monto", "dc_dir"),
        "dc_tx": _toggle_sort_href(request, "dc_ord", "tx", "dc_dir"),
        "sem_dia": _toggle_sort_href(request, "sem_ord", "dia", "sem_dir"),
        "sem_monto": _toggle_sort_href(request, "sem_ord", "monto", "sem_dir"),
        "sem_tx": _toggle_sort_href(request, "sem_ord", "tx", "sem_dir"),
        "mes_per": _toggle_sort_href(request, "mes_ord", "periodo", "mes_dir"),
        "mes_monto": _toggle_sort_href(request, "mes_ord", "monto", "mes_dir"),
        "mes_tx": _toggle_sort_href(request, "mes_ord", "tx", "mes_dir"),
    }

    months = [(i, f"{i:02d}") for i in range(1, 13)]

    return render(
        request,
        "core/analytics.html",
        {
            "star_model": star_model,
            "dim_tiempo_en_hechos": dim_tiempo_en_hechos,
            "ventas_por_dia_civil": ventas_por_dia_civil,
            "ventas_por_dia_semana": ventas_por_dia_semana,
            "ventas_por_mes_anio": ventas_por_mes_anio,
            "ej_orm_lunes_enero_2026": ej_orm_lunes_enero_2026,
            "top_clientes": list(top_clientes),
            "top_canales": list(top_canales),
            "top_productos": list(top_productos),
            "preview": preview,
            "filter_y": fy or "",
            "filter_m": fm or "",
            "filter_d": fd,
            "filter_summary": filter_summary,
            "dias_semana": DIAS_SEMANA_CHOICES,
            "years": years_for_select,
            "months": months,
            "sort_href": sort_href,
            "dw_span_min": dmin,
            "dw_span_max": dmax,
            "dw_total_unfiltered": dw_total_unfiltered,
            "years_with_sales": years_with_sales,
            "quick_time_links": quick_time_links,
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
