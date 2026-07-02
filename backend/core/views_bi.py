from __future__ import annotations

"""
Dashboard BI avanzado — estilo Power BI integrado en la app Django.

Tres pestañas:
  1. Ejecutivo  — KPIs, análisis temporal, por canal, geográfico.
  2. Comercial  — productos, clientes, canales.
  3. Análisis   — 6 preguntas de negocio respondidas automáticamente.

Medidas calculadas (equivalentes DAX):
  - Ventas Totales        = SUM(FactVentas.monto)
  - Cantidad de Ventas    = COUNT(FactVentas)
  - Venta Promedio        = AVG(FactVentas.monto)
  - Clientes Activos      = DISTINCTCOUNT(FactVentas.cliente_id)
  - Ventas Online         = SUM(monto) WHERE canal IN (web, app)
  - Ventas Presenciales   = SUM(monto) WHERE canal = pos
  - Participación Online  = Ventas Online / Ventas Totales
  - Participación Presencial = Ventas Presenciales / Ventas Totales
"""

from typing import Any

from django.db.models import Avg, Count, Sum, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from core.models import (
    DimCanal,
    DimCliente,
    DimProducto,
    DimTiempo,
    DimTienda,
    FactVentas,
)


# ── Canal label mapping ────────────────────────────────────────────────
_CANAL_DISPLAY: dict[str, str] = {
    "pos": "Tienda Física",
    "web": "Web",
    "app": "App",
}


def _canal_label(raw: str) -> str:
    return _CANAL_DISPLAY.get(raw, raw)


# ── Filters ────────────────────────────────────────────────────────────

def _apply_filters(qs, params: dict) -> tuple:
    """Apply slicer filters from querystring, return (filtered_qs, active_filters_dict)."""
    active: dict[str, Any] = {}

    y = params.get("y")
    if y and y != "todos":
        try:
            qs = qs.filter(fecha__anio=int(y))
            active["y"] = int(y)
        except (ValueError, TypeError):
            pass

    m = params.get("m")
    if m and m != "todos":
        try:
            qs = qs.filter(fecha__mes=int(m))
            active["m"] = int(m)
        except (ValueError, TypeError):
            pass

    canal = params.get("canal")
    if canal and canal != "todos":
        qs = qs.filter(canal__canal=canal)
        active["canal"] = canal

    region = params.get("region")
    if region and region != "todos":
        qs = qs.filter(tienda__region=region)
        active["region"] = region

    return qs, active


# ── Measures (DAX equivalents) ─────────────────────────────────────────

def _compute_measures(qs) -> dict[str, Any]:
    """Compute the 6 required DAX-equivalent measures + 2 participations."""
    agg = qs.aggregate(
        ventas_totales=Sum("monto"),
        cantidad_ventas=Count("id"),
        venta_promedio=Avg("monto"),
        clientes_activos=Count("cliente_id", distinct=True),
    )
    ventas_totales = agg["ventas_totales"] or 0
    cantidad_ventas = agg["cantidad_ventas"] or 0
    venta_promedio = int(agg["venta_promedio"] or 0)
    clientes_activos = agg["clientes_activos"] or 0

    ventas_online = qs.filter(
        canal__canal__in=["web", "app"]
    ).aggregate(t=Sum("monto"))["t"] or 0

    ventas_presenciales = qs.filter(
        canal__canal="pos"
    ).aggregate(t=Sum("monto"))["t"] or 0

    participacion_online = round(ventas_online / ventas_totales * 100, 1) if ventas_totales else 0
    participacion_presencial = round(ventas_presenciales / ventas_totales * 100, 1) if ventas_totales else 0

    return {
        "ventas_totales": ventas_totales,
        "cantidad_ventas": cantidad_ventas,
        "venta_promedio": venta_promedio,
        "clientes_activos": clientes_activos,
        "ventas_online": ventas_online,
        "ventas_presenciales": ventas_presenciales,
        "participacion_online": participacion_online,
        "participacion_presencial": participacion_presencial,
    }


# ── DAX formulas description ──────────────────────────────────────────

DAX_FORMULAS: list[dict[str, str]] = [
    {
        "nombre": "Ventas Totales",
        "dax": "Ventas Totales = SUM(FactVentas[monto])",
        "descripcion": "Suma del campo monto de todas las transacciones de venta. Representa el ingreso total generado.",
        "orm": "FactVentas.objects.aggregate(Sum('monto'))",
    },
    {
        "nombre": "Cantidad de Ventas",
        "dax": "Cantidad de Ventas = COUNTROWS(FactVentas)",
        "descripcion": "Cuenta el número total de transacciones registradas en la tabla de hechos.",
        "orm": "FactVentas.objects.count()",
    },
    {
        "nombre": "Venta Promedio",
        "dax": "Venta Promedio = AVERAGE(FactVentas[monto])",
        "descripcion": "Promedio del monto por transacción. Equivalente a DIVIDE(Ventas Totales, Cantidad de Ventas).",
        "orm": "FactVentas.objects.aggregate(Avg('monto'))",
    },
    {
        "nombre": "Clientes Activos",
        "dax": "Clientes Activos = DISTINCTCOUNT(FactVentas[cliente_id])",
        "descripcion": "Cantidad de clientes únicos que registran al menos una compra en el período filtrado.",
        "orm": "FactVentas.objects.aggregate(Count('cliente_id', distinct=True))",
    },
    {
        "nombre": "Ventas Online",
        "dax": 'Ventas Online = CALCULATE(SUM(FactVentas[monto]), DimCanal[canal] IN {"web", "app"})',
        "descripcion": "Total de ventas realizadas a través de canales digitales (Web y App).",
        "orm": "FactVentas.objects.filter(canal__canal__in=['web','app']).aggregate(Sum('monto'))",
    },
    {
        "nombre": "Ventas Presenciales",
        "dax": 'Ventas Presenciales = CALCULATE(SUM(FactVentas[monto]), DimCanal[canal] = "pos")',
        "descripcion": "Total de ventas realizadas en tiendas físicas (punto de venta presencial).",
        "orm": "FactVentas.objects.filter(canal__canal='pos').aggregate(Sum('monto'))",
    },
]


# ── Executive dashboard data ──────────────────────────────────────────

def _executive_data(qs) -> dict[str, Any]:
    """Data for the executive dashboard tab."""
    # Ventas por mes
    ventas_mes = list(
        qs.values("fecha__anio", "fecha__mes", "fecha__nombre_mes")
        .annotate(total=Sum("monto"), tx=Count("id"))
        .order_by("fecha__anio", "fecha__mes")
    )

    # Ventas por trimestre
    ventas_trimestre = list(
        qs.values("fecha__anio", "fecha__trimestre")
        .annotate(total=Sum("monto"), tx=Count("id"))
        .order_by("fecha__anio", "fecha__trimestre")
    )

    # Ventas por canal
    ventas_canal = list(
        qs.values("canal__canal")
        .annotate(total=Sum("monto"), tx=Count("id"))
        .order_by("-total")
    )
    for r in ventas_canal:
        r["canal_display"] = _canal_label(r["canal__canal"])

    # Ventas por región
    ventas_region = list(
        qs.filter(tienda__isnull=False)
        .values("tienda__region")
        .annotate(total=Sum("monto"), tx=Count("id"))
        .order_by("-total")
    )

    # Ventas por tienda
    ventas_tienda = list(
        qs.filter(tienda__isnull=False)
        .values("tienda__nombre_tienda", "tienda__region")
        .annotate(total=Sum("monto"), tx=Count("id"))
        .order_by("-total")
    )

    return {
        "ventas_mes": ventas_mes,
        "ventas_trimestre": ventas_trimestre,
        "ventas_canal": ventas_canal,
        "ventas_region": ventas_region,
        "ventas_tienda": ventas_tienda,
    }


# ── Commercial dashboard data ─────────────────────────────────────────

def _commercial_data(qs) -> dict[str, Any]:
    """Data for the commercial dashboard tab."""
    # Top 10 productos
    top_productos = list(
        qs.filter(producto__isnull=False)
        .values("producto__id_producto", "producto__nombre_producto", "producto__categoria")
        .annotate(total=Sum("monto"), unidades=Sum("cantidad"))
        .order_by("-total")[:10]
    )

    # Ventas por categoría
    ventas_categoria = list(
        qs.filter(producto__isnull=False)
        .values("producto__categoria")
        .annotate(total=Sum("monto"), tx=Count("id"))
        .order_by("-total")
    )

    # Ventas por segmento de clientes
    ventas_segmento = list(
        qs.values("cliente__segmento")
        .annotate(total=Sum("monto"), tx=Count("id"), n_clientes=Count("cliente_id", distinct=True))
        .order_by("-total")
    )

    # Ventas por ciudad
    ventas_ciudad = list(
        qs.values("cliente__ciudad")
        .annotate(total=Sum("monto"), tx=Count("id"))
        .order_by("-total")[:15]
    )

    # Comparación entre canales (detallada)
    canales_comparacion = list(
        qs.values("canal__canal")
        .annotate(
            total=Sum("monto"),
            tx=Count("id"),
            ticket_promedio=Avg("monto"),
            n_clientes=Count("cliente_id", distinct=True),
        )
        .order_by("-total")
    )
    for r in canales_comparacion:
        r["canal_display"] = _canal_label(r["canal__canal"])
        r["ticket_promedio"] = int(r["ticket_promedio"] or 0)

    return {
        "top_productos": top_productos,
        "ventas_categoria": ventas_categoria,
        "ventas_segmento": ventas_segmento,
        "ventas_ciudad": ventas_ciudad,
        "canales_comparacion": canales_comparacion,
    }


# ── Business analysis (6 questions) ──────────────────────────────────

def _business_analysis(qs) -> list[dict[str, str]]:
    """Auto-answer the 6 business questions from the evaluation rubric."""
    answers: list[dict[str, str]] = []

    # 1. Canal con mayores ingresos
    top_canal = (
        qs.values("canal__canal")
        .annotate(total=Sum("monto"))
        .order_by("-total")
        .first()
    )
    if top_canal:
        label = _canal_label(top_canal["canal__canal"])
        monto = f"${top_canal['total']:,.0f}".replace(",", ".")
        answers.append({
            "numero": "1",
            "pregunta": "¿Cuál es el canal que genera mayores ingresos?",
            "respuesta": f"El canal <strong>{label}</strong> genera los mayores ingresos con un total de <strong>{monto}</strong>.",
            "evidencia": "Gráfico: Ventas por Canal (Dashboard Ejecutivo)",
        })

    # 2. Mejor categoría de productos
    top_cat = (
        qs.filter(producto__isnull=False)
        .values("producto__categoria")
        .annotate(total=Sum("monto"))
        .order_by("-total")
        .first()
    )
    if top_cat:
        monto = f"${top_cat['total']:,.0f}".replace(",", ".")
        answers.append({
            "numero": "2",
            "pregunta": "¿Qué categoría de productos presenta mejores resultados?",
            "respuesta": f"La categoría <strong>{top_cat['producto__categoria']}</strong> lidera con <strong>{monto}</strong> en ventas.",
            "evidencia": "Gráfico: Ventas por Categoría (Dashboard Comercial)",
        })

    # 3. Segmento de clientes que aporta más ventas
    top_seg = (
        qs.values("cliente__segmento")
        .annotate(total=Sum("monto"))
        .order_by("-total")
        .first()
    )
    if top_seg:
        monto = f"${top_seg['total']:,.0f}".replace(",", ".")
        answers.append({
            "numero": "3",
            "pregunta": "¿Qué segmento de clientes aporta más ventas?",
            "respuesta": f"El segmento <strong>{top_seg['cliente__segmento']}</strong> aporta el mayor volumen de ventas con <strong>{monto}</strong>.",
            "evidencia": "Gráfico: Ventas por Segmento (Dashboard Comercial)",
        })

    # 4. Tienda con mejor desempeño
    top_tienda = (
        qs.filter(tienda__isnull=False)
        .values("tienda__nombre_tienda")
        .annotate(total=Sum("monto"))
        .order_by("-total")
        .first()
    )
    if top_tienda:
        monto = f"${top_tienda['total']:,.0f}".replace(",", ".")
        answers.append({
            "numero": "4",
            "pregunta": "¿Qué tienda presenta el mejor desempeño comercial?",
            "respuesta": f"La tienda <strong>{top_tienda['tienda__nombre_tienda']}</strong> es la de mejor desempeño con <strong>{monto}</strong> en ventas.",
            "evidencia": "Tabla: Ventas por Tienda (Dashboard Ejecutivo)",
        })
    else:
        answers.append({
            "numero": "4",
            "pregunta": "¿Qué tienda presenta el mejor desempeño comercial?",
            "respuesta": "No hay datos de tienda disponibles. Las ventas online no tienen tienda asignada.",
            "evidencia": "N/A — cargar datos con tienda asignada",
        })

    # 5. Tendencias
    meses = list(
        qs.values("fecha__anio", "fecha__mes")
        .annotate(total=Sum("monto"))
        .order_by("fecha__anio", "fecha__mes")
    )
    if len(meses) >= 2:
        first_month = meses[0]
        last_month = meses[-1]
        cambio = last_month["total"] - first_month["total"]
        direccion = "creciente" if cambio > 0 else "decreciente" if cambio < 0 else "estable"
        answers.append({
            "numero": "5",
            "pregunta": "¿Qué tendencias pueden observarse en los datos?",
            "respuesta": f"Se observa una tendencia <strong>{direccion}</strong> en las ventas. "
                         f"El primer período registró ${first_month['total']:,.0f} y el último ${last_month['total']:,.0f}.".replace(",", "."),
            "evidencia": "Gráfico: Ventas por Mes (Dashboard Ejecutivo)",
        })
    else:
        answers.append({
            "numero": "5",
            "pregunta": "¿Qué tendencias pueden observarse en los datos?",
            "respuesta": "Se necesitan datos de al menos dos períodos para analizar tendencias.",
            "evidencia": "N/A",
        })

    # 6. Decisiones gerenciales
    decisions = []
    # Decision based on channel performance
    if top_canal:
        label = _canal_label(top_canal["canal__canal"])
        decisions.append(f"Fortalecer la inversión en el canal <strong>{label}</strong>, que genera el mayor ingreso.")
    if top_cat:
        decisions.append(f"Ampliar el catálogo de la categoría <strong>{top_cat['producto__categoria']}</strong>, que es la más demandada.")
    if top_seg:
        decisions.append(f"Diseñar programas de fidelización para el segmento <strong>{top_seg['cliente__segmento']}</strong>, que representa el mayor volumen de compra.")
    if not decisions:
        decisions = ["Cargar más datos para generar recomendaciones basadas en evidencia."]

    answers.append({
        "numero": "6",
        "pregunta": "¿Qué tres decisiones podría tomar la gerencia utilizando esta información?",
        "respuesta": "<ol>" + "".join(f"<li>{d}</li>" for d in decisions[:3]) + "</ol>",
        "evidencia": "Todos los dashboards — análisis integrado",
    })

    return answers


# ── Main view ─────────────────────────────────────────────────────────

def bi_dashboard(request: HttpRequest) -> HttpResponse:
    """Main BI dashboard view with 3 tabs."""
    tab = (request.GET.get("tab") or "ejecutivo").lower()
    if tab not in ("ejecutivo", "comercial", "analisis"):
        tab = "ejecutivo"

    qs = FactVentas.objects.select_related("fecha", "cliente", "producto", "canal", "tienda")
    qs, active_filters = _apply_filters(qs, request.GET)

    measures = _compute_measures(qs)

    # Star model counts
    star_model = {
        "dim_cliente": DimCliente.objects.count(),
        "dim_producto": DimProducto.objects.count(),
        "dim_tiempo": DimTiempo.objects.count(),
        "dim_canal": DimCanal.objects.count(),
        "dim_tienda": DimTienda.objects.count(),
        "fact_ventas": FactVentas.objects.count(),
        "fact_filtrado": qs.count(),
    }

    # Available filter options
    years = sorted(set(
        FactVentas.objects.values_list("fecha__anio", flat=True).distinct()
    ))
    canales = list(DimCanal.objects.values_list("canal", flat=True).order_by("canal"))
    regiones = sorted(set(
        DimTienda.objects.values_list("region", flat=True).distinct()
    ))

    ctx: dict[str, Any] = {
        "tab": tab,
        "measures": measures,
        "star_model": star_model,
        "active_filters": active_filters,
        "filter_years": years,
        "filter_canales": canales,
        "filter_regiones": regiones,
        "dax_formulas": DAX_FORMULAS,
    }

    if tab == "ejecutivo":
        ctx["exec_data"] = _executive_data(qs)
    elif tab == "comercial":
        ctx["comm_data"] = _commercial_data(qs)
    elif tab == "analisis":
        ctx["analysis"] = _business_analysis(qs)
        ctx["comm_data"] = _commercial_data(qs)
        ctx["exec_data"] = _executive_data(qs)

    return render(request, "core/bi_dashboard.html", ctx)


def bi_api_data(request: HttpRequest) -> JsonResponse:
    """JSON API endpoint for AJAX chart updates when filters change."""
    qs = FactVentas.objects.select_related("fecha", "cliente", "producto", "canal", "tienda")
    qs, active_filters = _apply_filters(qs, request.GET)

    measures = _compute_measures(qs)
    exec_data = _executive_data(qs)
    comm_data = _commercial_data(qs)

    # Serialize dates
    for r in exec_data.get("ventas_mes", []):
        pass  # already serializable
    for r in exec_data.get("ventas_tienda", []):
        pass

    return JsonResponse({
        "measures": measures,
        "exec_data": exec_data,
        "comm_data": comm_data,
        "filters": active_filters,
    })
