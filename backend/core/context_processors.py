"""Opciones de filtro para el menú lateral (todas las páginas con appShell)."""
from __future__ import annotations

from core.models import FactVentas
from core.views import DIAS_SEMANA_CHOICES


def sidebar_dw_options(request) -> dict:
    years_with_sales = sorted(
        {y for y in FactVentas.objects.values_list("fecha__anio", flat=True).distinct() if y}
    )
    years_for_select = sorted(set(range(2000, 2036)) | set(years_with_sales))
    months_for_select = [(i, f"{i:02d}") for i in range(1, 13)]
    return {
        "sidebar_years": years_for_select,
        "sidebar_months": months_for_select,
        "sidebar_dias": DIAS_SEMANA_CHOICES,
    }
