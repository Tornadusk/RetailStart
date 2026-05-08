"""Generación de filas DimTiempo (calendario) para el DW."""

from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction

from core.models import DimTiempo

NOMBRES_DIA = (
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
)

NOMBRES_MES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


def fecha_a_id_tiempo(d: date) -> int:
    return int(d.strftime("%Y%m%d"))


@transaction.atomic
def seed_dim_tiempo_calendar(year_from: int, year_to: int) -> int:
    """
    Pre-puebla DimTiempo para [year_from, year_to] inclusive (un registro por día).
    Devuelve cuántos objetos intentó crear (ignora duplicados por PK si ya existen).
    """
    start = date(year_from, 1, 1)
    end = date(year_to, 12, 31)

    objs: list[DimTiempo] = []
    d = start
    while d <= end:
        dow = d.isoweekday()  # 1=Lunes … 7=Domingo
        objs.append(
            DimTiempo(
                id_tiempo=fecha_a_id_tiempo(d),
                fecha_completa=d,
                dia_semana=dow,
                nombre_dia=NOMBRES_DIA[dow - 1],
                dia_mes=d.day,
                mes=d.month,
                nombre_mes=NOMBRES_MES[d.month - 1],
                trimestre=(d.month - 1) // 3 + 1,
                anio=d.year,
                es_fin_semana=dow >= 6,
            )
        )
        d += timedelta(days=1)

    DimTiempo.objects.bulk_create(objs, ignore_conflicts=True)
    return len(objs)
