"""Opciones de filtro para el menú lateral (todas las páginas con appShell)."""
from __future__ import annotations

from core.models import FactVentas
from core.views import DIAS_SEMANA_CHOICES


def sidebar_dw_options(request) -> dict:
    years_with_sales = sorted(
        {y for y in FactVentas.objects.values_list("fecha__anio", flat=True).distinct() if y}
    )
    years_for_select = sorted(set(range(2000, 2036)) | set(years_with_sales))
    dias_labels = [label for val, label in DIAS_SEMANA_CHOICES if val]
    return {
        "sidebar_years": years_for_select,
        "sidebar_dias": dias_labels,
    }
