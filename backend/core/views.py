from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from html import escape
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Max, Min, QuerySet, Sum
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

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
_DASHBOARD_FILTERS_ANCHOR = "#dashboard-filters"


def _is_filter_todos_token(val: str | None) -> bool:
    if val is None:
        return True
    s = str(val).strip().lower()
    return s in ("", "todos", "todo", "all", "*")


def _parse_optional_year(val: str | None) -> int | None:
    if _is_filter_todos_token(val):
        return None
    try:
        y = int(str(val).strip())
    except ValueError:
        return None
    return y if 1990 <= y <= 2100 else None


def _parse_optional_month(val: str | None) -> int | None:
    if _is_filter_todos_token(val):
        return None
    try:
        m = int(str(val).strip())
    except ValueError:
        return None
    return m if 1 <= m <= 12 else None


def _parse_iso_date(val: str | None) -> date | None:
    if val is None or not str(val).strip():
        return None
    s = str(val).strip()
    parts = s.split("-")
    if len(parts) != 3:
        return None
    try:
        y, mo, d = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if not (1990 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31):
        return None
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _filter_fact_qs(
    qs: QuerySet,
    *,
    y: int | None,
    m: int | None,
    dia: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet:
    if date_from is not None and date_to is not None and date_from <= date_to:
        return qs.filter(fecha__fecha_completa__gte=date_from, fecha__fecha_completa__lte=date_to)
    if y is not None:
        qs = qs.filter(fecha__anio=y)
    if m is not None:
        qs = qs.filter(fecha__mes=m)
    if dia:
        qs = qs.filter(fecha__nombre_dia=dia)
    return qs


def _analytics_anchor_date(today: date, dmin: date, dmax: date) -> date:
    """Fecha de calendario para presets: hoy si cae dentro del DW; si no, el borde más cercano."""
    if today < dmin:
        return dmin
    if today > dmax:
        return dmax
    return today


def _order_prefix(direction: str | None) -> str:
    return "-" if (direction or "asc").lower() == "desc" else ""


def _analytics_filter_qs(params: dict[str, Any], anchor: str | None = None) -> str:
    """Querystring solo con filtros de tiempo (sin parámetros de orden)."""
    clean = {k: v for k, v in params.items() if v is not None and str(v) != ""}
    base = "?" + urlencode(clean) if clean else "?"
    suf = anchor if anchor is not None else _ANALYTICS_FILTROS_ANCHOR
    return base + suf


_FACT_PREVIEW_PER_PAGE = 50
_FACT_PREVIEW_PAGE_PARAM = "fact_page"


def _fact_preview_page_url(request: HttpRequest, page_num: int) -> str:
    """Conserva filtros y orden en la query; ancla a la vista de hechos."""
    q = request.GET.copy()
    if page_num <= 1:
        q.pop(_FACT_PREVIEW_PAGE_PARAM, None)
    else:
        q[_FACT_PREVIEW_PAGE_PARAM] = str(page_num)
    path = reverse("analytics")
    qs = q.urlencode()
    return f"{path}?{qs}#dw-vista-hechos" if qs else f"{path}#dw-vista-hechos"


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


def _dw_time_filter_bundle(
    request: HttpRequest,
    *,
    preset_anchor: str,
) -> tuple[QuerySet[FactVentas], dict[str, Any]]:
    """
    Filtros de hechos por tiempo (?y=&m=&d= o rango ?fde=&fha=), alineados con /analytics/.
    `preset_anchor` se anexa a los href de atajos (ej. #segmentar-ventas o #dashboard-filters).
    """
    fy = _parse_optional_year(request.GET.get("y"))
    fm = _parse_optional_month(request.GET.get("m"))
    raw_d = request.GET.get("d")
    fd = "" if _is_filter_todos_token(raw_d) else (raw_d or "").strip()
    fde = _parse_iso_date(request.GET.get("fde"))
    fha = _parse_iso_date(request.GET.get("fha"))
    range_active = fde is not None and fha is not None and fde <= fha

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

    dmin, dmax = agg_dates["dmin"], agg_dates["dmax"]

    filter_parts: list[str] = []
    if range_active:
        assert fde is not None and fha is not None
        filter_parts.append(
            f"Rango del {fde.strftime('%d/%m/%Y')} al {fha.strftime('%d/%m/%Y')}"
        )
    else:
        if fy is not None:
            filter_parts.append(f"Año {fy}")
        if fm is not None:
            filter_parts.append(f"Mes {fm:02d}")
        if fd:
            filter_parts.append(fd)
    filter_summary = " · ".join(filter_parts) if filter_parts else "Sin filtros (todos los hechos)"

    quick_time_links: list[dict[str, str]] = []
    if dmin is not None and dmax is not None:
        anchor_date = _analytics_anchor_date(date.today(), dmin, dmax)
        y_ref, m_ref = anchor_date.year, anchor_date.month
        quick_time_links.append(
            {"label": "Año actual", "href": _analytics_filter_qs({"y": y_ref}, preset_anchor)}
        )
        quick_time_links.append(
            {
                "label": "Mes actual",
                "href": _analytics_filter_qs({"y": y_ref, "m": m_ref}, preset_anchor),
            }
        )
        monday = anchor_date - timedelta(days=anchor_date.weekday())
        sunday = monday + timedelta(days=6)
        w0, w1 = max(monday, dmin), min(sunday, dmax)
        if w0 <= w1:
            quick_time_links.append(
                {
                    "label": "Semana actual",
                    "href": _analytics_filter_qs(
                        {"fde": w0.isoformat(), "fha": w1.isoformat()},
                        preset_anchor,
                    ),
                }
            )
        quick_time_links.extend(
            [
                {"label": "Solo lunes", "href": _analytics_filter_qs({"d": "Lunes"}, preset_anchor)},
                {"label": "Solo domingos", "href": _analytics_filter_qs({"d": "Domingo"}, preset_anchor)},
                {
                    "label": "Domingos del mes actual",
                    "href": _analytics_filter_qs(
                        {"y": y_ref, "m": m_ref, "d": "Domingo"},
                        preset_anchor,
                    ),
                },
            ]
        )
    quick_time_links.append({"label": "Quitar filtros", "href": "?" + preset_anchor})

    if range_active:
        assert fde is not None and fha is not None
        qs = _filter_fact_qs(facts_all, y=None, m=None, dia="", date_from=fde, date_to=fha)
        form_select_y: int | str = ""
        form_select_m: int | str = ""
        form_select_d = ""
    else:
        qs = _filter_fact_qs(facts_all, y=fy, m=fm, dia=fd)
        form_select_y = fy if fy is not None else ""
        form_select_m = fm if fm is not None else ""
        form_select_d = fd

    months = [(i, f"{i:02d}") for i in range(1, 13)]
    meta: dict[str, Any] = {
        "filter_range_active": range_active,
        "filter_fde": fde if range_active else None,
        "filter_fha": fha if range_active else None,
        "filter_y": form_select_y,
        "filter_m": form_select_m,
        "filter_d": form_select_d,
        "filter_summary": filter_summary,
        "dias_semana": DIAS_SEMANA_CHOICES,
        "years": years_for_select,
        "months": months,
        "quick_time_links": quick_time_links,
        "dw_span_min": dmin,
        "dw_span_max": dmax,
        "dw_total_unfiltered": dw_total_unfiltered,
        "years_with_sales": years_with_sales,
    }
    return qs, meta


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
            "desc": "Dashboard web (/dashboard/: gráficos Chart.js + tablas), PNG + KPIs (/evidence/) y tablas agregadas vía ORM (/analytics/).",
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
               · Querystring ?y=&m=&d= o rango ?fde=&fha= (YYYY-MM-DD, inclusivo) filtra hechos (`_dw_time_filter_bundle` → `_filter_fact_qs`).
               · Agregaciones `.values(...).annotate(...)` = GROUP BY en SQL.
               · `preview` página de hechos con `select_related` y paginación (`fact_page`).

    Parte 5 actividad: mejores clientes, canal, producto; más cortes por dimensión tiempo.
    """

    # Filtros de tiempo y meta del formulario compartidos con `dashboard()` via `_dw_time_filter_bundle`:
    # misma querystring, mismos quick links (anchor distinto: #segmentar-ventas). No se cambió el
    # comportamiento respecto a la lógica duplicada anterior; solo se unificó la fuente de verdad.

    qs, meta = _dw_time_filter_bundle(request, preset_anchor=_ANALYTICS_FILTROS_ANCHOR)

    dmin, dmax = meta["dw_span_min"], meta["dw_span_max"]
    ej_ref_year = date.today().year
    if dmin is not None and dmax is not None:
        ej_ref_year = _analytics_anchor_date(date.today(), dmin, dmax).year

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

    ej_orm_lunes_enero_ref = (
        qs.filter(
            fecha__nombre_dia="Lunes",
            fecha__nombre_mes="Enero",
            fecha__anio=ej_ref_year,
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

    preview_qs = qs.select_related("cliente", "producto", "canal", "fecha").order_by(
        "-fecha__fecha_completa", "-id"
    )
    preview_paginator = Paginator(preview_qs, _FACT_PREVIEW_PER_PAGE)
    preview_nav: dict[str, Any]
    preview: list[dict[str, Any]] = []

    if preview_paginator.count == 0:
        preview_nav = {
            "empty": True,
            "total": 0,
            "has_previous": False,
            "has_next": False,
            "prev_url": None,
            "next_url": None,
            "num_pages": 0,
            "number": 0,
            "start_index": 0,
            "end_index": 0,
        }
    else:
        page_obj = preview_paginator.get_page(request.GET.get(_FACT_PREVIEW_PAGE_PARAM))
        for fv in page_obj:
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
        preview_nav = {
            "empty": False,
            "total": preview_paginator.count,
            "has_previous": page_obj.has_previous(),
            "has_next": page_obj.has_next(),
            "prev_url": (
                _fact_preview_page_url(request, page_obj.previous_page_number())
                if page_obj.has_previous()
                else None
            ),
            "next_url": (
                _fact_preview_page_url(request, page_obj.next_page_number())
                if page_obj.has_next()
                else None
            ),
            "num_pages": preview_paginator.num_pages,
            "number": page_obj.number,
            "start_index": page_obj.start_index(),
            "end_index": page_obj.end_index(),
        }

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

    return render(
        request,
        "core/analytics.html",
        {
            **meta,
            "star_model": star_model,
            "dim_tiempo_en_hechos": dim_tiempo_en_hechos,
            "ventas_por_dia_civil": ventas_por_dia_civil,
            "ventas_por_dia_semana": ventas_por_dia_semana,
            "ventas_por_mes_anio": ventas_por_mes_anio,
            "ej_orm_lunes_enero_ref": ej_orm_lunes_enero_ref,
            "ej_ref_year": ej_ref_year,
            "top_clientes": list(top_clientes),
            "top_canales": list(top_canales),
            "top_productos": list(top_productos),
            "preview": preview,
            "preview_nav": preview_nav,
            "fact_preview_per_page": _FACT_PREVIEW_PER_PAGE,
            "sort_href": sort_href,
        },
    )


def _dashboard_view_qs(request: HttpRequest, view: str) -> str:
    q = request.GET.copy()
    q["view"] = view
    return q.urlencode()


_DASHBOARD_PANEL_KEYS: tuple[str, ...] = ("canal", "clientes", "dia", "dow", "productos")

# Paneles dashboard: mismos stems/ids que en `dashboard.html` (export combinado vista «Todos»).
_DASHBOARD_BUNDLE_MANIFEST: list[dict[str, str]] = [
    {
        "canvasId": "chart-canal",
        "stem": "retailstart_dashboard_canal",
        "title": "Por canal",
        "tableWrapId": "dashboard-table-canal",
    },
    {
        "canvasId": "chart-clientes",
        "stem": "retailstart_dashboard_clientes",
        "title": "Top clientes · barras horizontales",
        "tableWrapId": "dashboard-table-clientes",
    },
    {
        "canvasId": "chart-dia",
        "stem": "retailstart_dashboard_dia",
        "title": "Por día civil · barras",
        "tableWrapId": "dashboard-table-dia",
    },
    {
        "canvasId": "chart-dow",
        "stem": "retailstart_dashboard_dow",
        "title": "Por día de la semana",
        "tableWrapId": "dashboard-table-dow",
    },
    {
        "canvasId": "chart-productos",
        "stem": "retailstart_dashboard_productos",
        "title": "Top productos · barras horizontales",
        "tableWrapId": "dashboard-table-productos",
    },
]


def _dashboard_agg_rows(qs: QuerySet) -> dict[str, list]:
    """Agregaciones del dashboard (mismos límites que los gráficos en pantalla)."""
    return {
        "canal": list(qs.values("canal__canal").annotate(total=Sum("monto")).order_by("-total")),
        "clientes": list(
            qs.values(
                "cliente__id_cliente",
                "cliente__nombre",
                "cliente__apellido",
                "cliente__segmento",
            )
            .annotate(total=Sum("monto"))
            .order_by("-total")[:10]
        ),
        "dia": list(
            qs.values("fecha__fecha_completa", "fecha__nombre_dia")
            .annotate(total=Sum("monto"), tx=Count("id"))
            .order_by("fecha__fecha_completa")
        ),
        "dow": list(
            qs.values("fecha__nombre_dia", "fecha__dia_semana")
            .annotate(total=Sum("monto"))
            .order_by("fecha__dia_semana")
        ),
        "productos": list(
            qs.values(
                "producto__id_producto",
                "producto__nombre_producto",
            )
            .annotate(total=Sum("monto"))
            .order_by("-total")[:10]
        ),
    }


def _dashboard_chart_payload(
    rows_map: dict[str, list],
    *,
    total_monto: int,
    n_tx: int,
) -> dict[str, Any]:
    by_canal = rows_map["canal"]
    top_clientes = rows_map["clientes"]
    by_dia = rows_map["dia"]
    by_dow = rows_map["dow"]
    top_productos = rows_map["productos"]
    return {
        "by_canal": {
            "labels": [str(r["canal__canal"] or "?") for r in by_canal],
            "values": [int(r["total"] or 0) for r in by_canal],
        },
        "top_clientes": {
            "labels": [
                f'{r["cliente__nombre"]} {r["cliente__apellido"]}'.strip()[:40]
                for r in top_clientes
            ],
            "values": [int(r["total"] or 0) for r in top_clientes],
        },
        "by_dia": {
            "labels": [
                (
                    r["fecha__fecha_completa"].isoformat()
                    if r.get("fecha__fecha_completa")
                    else ""
                )
                for r in by_dia
            ],
            "values": [int(r["total"] or 0) for r in by_dia],
        },
        "by_dow": {
            "labels": [str(r["fecha__nombre_dia"] or "") for r in by_dow],
            "values": [int(r["total"] or 0) for r in by_dow],
        },
        "top_productos": {
            "labels": [
                (
                    str(r["producto__nombre_producto"])
                    if r["producto__nombre_producto"]
                    else "Sin producto"
                )[:36]
                for r in top_productos
            ],
            "values": [int(r["total"] or 0) for r in top_productos],
        },
        "kpis": {
            "total_monto": int(total_monto),
            "transacciones": n_tx,
            "ticket_promedio": int(total_monto // n_tx) if n_tx else 0,
        },
    }


def _dashboard_export_resolve_panels(request: HttpRequest) -> tuple[list[str], str | None]:
    """Lista de paneles a incluir en export; `single_panel` solo si es export por tarjeta."""
    raw = (request.GET.get("panel") or "").strip().lower()
    all_keys = list(_DASHBOARD_PANEL_KEYS)
    if not raw or raw == "all":
        return all_keys, None
    if raw in _DASHBOARD_PANEL_KEYS:
        return [raw], raw
    return all_keys, None


def dashboard(request: HttpRequest) -> HttpResponse:
    qs, meta = _dw_time_filter_bundle(request, preset_anchor=_DASHBOARD_FILTERS_ANCHOR)
    view_mode = (request.GET.get("view") or "charts").lower()
    if view_mode not in ("charts", "tables", "both"):
        view_mode = "charts"

    star_model = {
        "dim_cliente": DimCliente.objects.count(),
        "dim_producto": DimProducto.objects.count(),
        "dim_tiempo": DimTiempo.objects.count(),
        "dim_canal": DimCanal.objects.count(),
        "fact_ventas": FactVentas.objects.count(),
        "hechos_filtrados": qs.count(),
    }

    rows_map = _dashboard_agg_rows(qs)
    total_monto = qs.aggregate(t=Sum("monto"))["t"] or 0
    n_tx = qs.count()
    chart_payload = _dashboard_chart_payload(
        rows_map,
        total_monto=int(total_monto),
        n_tx=n_tx,
    )

    ctx = {
        **meta,
        "star_model": star_model,
        "view_mode": view_mode,
        "by_canal_rows": rows_map["canal"],
        "top_clientes_rows": rows_map["clientes"],
        "by_dia_rows": rows_map["dia"],
        "by_dow_rows": rows_map["dow"],
        "top_productos_rows": rows_map["productos"],
        "chart_payload": chart_payload,
        "export_querystring": request.GET.urlencode(),
        "qs_view_charts": _dashboard_view_qs(request, "charts"),
        "qs_view_tables": _dashboard_view_qs(request, "tables"),
        "qs_view_both": _dashboard_view_qs(request, "both"),
        "dashboard_bundle_manifest": _DASHBOARD_BUNDLE_MANIFEST,
    }
    return render(request, "core/dashboard.html", ctx)


def _dashboard_export_append_csv_panel(w: csv.writer, panel: str, rows_map: dict[str, list]) -> None:
    rows = rows_map[panel]
    if panel == "canal":
        w.writerow(["Por canal"])
        w.writerow(["Canal", "Total"])
        for r in rows:
            w.writerow([r["canal__canal"], r["total"]])
        return
    if panel == "clientes":
        w.writerow(["Top clientes"])
        w.writerow(["Cliente id", "Nombre", "Apellido", "Segmento", "Total"])
        for r in rows:
            w.writerow(
                [
                    r["cliente__id_cliente"],
                    r["cliente__nombre"],
                    r["cliente__apellido"],
                    r["cliente__segmento"],
                    r["total"],
                ]
            )
        return
    if panel == "dia":
        w.writerow(["Por día civil"])
        w.writerow(["Fecha", "Día", "Transacciones", "Total"])
        for r in rows:
            fc = r["fecha__fecha_completa"]
            w.writerow(
                [
                    fc.isoformat() if fc else "",
                    r["fecha__nombre_dia"],
                    r["tx"],
                    r["total"],
                ]
            )
        return
    if panel == "dow":
        w.writerow(["Por día de la semana"])
        w.writerow(["Día", "Número ISO (día)", "Total"])
        for r in rows:
            w.writerow([r["fecha__nombre_dia"], r["fecha__dia_semana"], r["total"]])
        return
    if panel == "productos":
        w.writerow(["Top productos"])
        w.writerow(["Producto id", "Nombre", "Total"])
        for r in rows:
            w.writerow([r["producto__id_producto"], r["producto__nombre_producto"], r["total"]])


def _dashboard_export_append_html_panel(parts: list[str], panel: str, rows_map: dict[str, list]) -> None:
    rows = rows_map[panel]
    if panel == "canal":
        parts.append("<h2>Por canal</h2><table><tr><th>Canal</th><th>Total</th></tr>")
        for r in rows:
            parts.append(
                f"<tr><td>{escape(str(r['canal__canal'] or ''))}</td>"
                f"<td>{r['total']}</td></tr>"
            )
        parts.append("</table>")
        return
    if panel == "clientes":
        parts.append(
            "<h2>Top clientes</h2><table><tr>"
            "<th>ID</th><th>Nombre</th><th>Apellido</th><th>Segmento</th><th>Total</th></tr>"
        )
        for r in rows:
            parts.append(
                "<tr>"
                f"<td>{r['cliente__id_cliente']}</td>"
                f"<td>{escape(str(r['cliente__nombre'] or ''))}</td>"
                f"<td>{escape(str(r['cliente__apellido'] or ''))}</td>"
                f"<td>{escape(str(r['cliente__segmento'] or ''))}</td>"
                f"<td>{r['total']}</td>"
                "</tr>"
            )
        parts.append("</table>")
        return
    if panel == "dia":
        parts.append(
            "<h2>Por día civil</h2><table><tr>"
            "<th>Fecha</th><th>Día</th><th>Transacciones</th><th>Total</th></tr>"
        )
        for r in rows:
            fc = r["fecha__fecha_completa"]
            fds = fc.isoformat() if fc else ""
            parts.append(
                "<tr>"
                f"<td>{escape(fds)}</td>"
                f"<td>{escape(str(r['fecha__nombre_dia'] or ''))}</td>"
                f"<td>{r['tx']}</td>"
                f"<td>{r['total']}</td>"
                "</tr>"
            )
        parts.append("</table>")
        return
    if panel == "dow":
        parts.append(
            "<h2>Por día de la semana</h2><table><tr>"
            "<th>Día</th><th>Número ISO</th><th>Total</th></tr>"
        )
        for r in rows:
            parts.append(
                "<tr>"
                f"<td>{escape(str(r['fecha__nombre_dia'] or ''))}</td>"
                f"<td>{r['fecha__dia_semana']}</td>"
                f"<td>{r['total']}</td>"
                "</tr>"
            )
        parts.append("</table>")
        return
    if panel == "productos":
        parts.append("<h2>Top productos</h2><table><tr><th>ID</th><th>Producto</th><th>Total</th></tr>")
        for r in rows:
            parts.append(
                "<tr>"
                f"<td>{escape(str(r['producto__id_producto'] or ''))}</td>"
                f"<td>{escape(str(r['producto__nombre_producto'] or ''))}</td>"
                f"<td>{r['total']}</td>"
                "</tr>"
            )
        parts.append("</table>")
        return


def dashboard_export(request: HttpRequest, fmt: str) -> HttpResponse:
    fmt_norm = fmt.lower().strip()
    if fmt_norm not in ("csv", "html", "pdf", "xlsx"):
        raise Http404("Unsupported format")

    qs, meta = _dw_time_filter_bundle(request, preset_anchor=_DASHBOARD_FILTERS_ANCHOR)
    panels, single_panel = _dashboard_export_resolve_panels(request)
    rows_map = _dashboard_agg_rows(qs)
    summary_html = escape(meta.get("filter_summary") or "")
    slug = "dashboard" if len(panels) > 1 else f"dashboard_{panels[0]}"

    if fmt_norm == "csv":
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["RetailStart dashboard export"])
        w.writerow([meta.get("filter_summary") or ""])
        w.writerow([])
        for i, panel in enumerate(panels):
            if i:
                w.writerow([])
            _dashboard_export_append_csv_panel(w, panel, rows_map)
        resp = HttpResponse(buf.getvalue(), content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="retailstart_{slug}.csv"'
        return resp

    if fmt_norm == "html":
        doc_title = (
            "RetailStart — Dashboard"
            if len(panels) > 1
            else f"RetailStart — Dashboard ({panels[0]})"
        )
        parts = [
            "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>",
            f"<title>{escape(doc_title)}</title>",
            "<style>body{font-family:system-ui,sans-serif;background:#111;color:#eee;padding:24px;}",
            "table{border-collapse:collapse;width:100%;margin-bottom:28px;}th,td{border:1px solid #444;padding:8px;text-align:left;}",
            "th{background:#222;color:#9cf;}h1{color:#9cf;}h2{font-size:1rem;color:#aad;}</style></head><body>",
            f"<h1>{escape(doc_title)}</h1><p>{summary_html}</p>",
        ]
        for panel in panels:
            _dashboard_export_append_html_panel(parts, panel, rows_map)
        parts.append("</body></html>")
        html = "".join(parts)
        resp = HttpResponse(html, content_type="text/html; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="retailstart_{slug}.html"'
        return resp

    if fmt_norm == "xlsx":
        from core.dashboard_xlsx_export import build_dashboard_xlsx_bytes

        xlsx_blob = build_dashboard_xlsx_bytes(
            panels=list(panels),
            rows_map=rows_map,
            filter_summary=str(meta.get("filter_summary") or ""),
        )
        resp = HttpResponse(
            xlsx_blob,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = f'attachment; filename="retailstart_{slug}.xlsx"'
        return resp

    return render(
        request,
        "core/dashboard_print.html",
        {
            "filter_summary": meta.get("filter_summary") or "",
            "single_panel": single_panel,
            "by_canal_rows": rows_map["canal"],
            "top_clientes_rows": rows_map["clientes"],
            "by_dia_rows": rows_map["dia"],
            "by_dow_rows": rows_map["dow"],
            "top_productos_rows": rows_map["productos"],
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
