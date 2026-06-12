from __future__ import annotations

"""
Auditoría del pipeline incremental RetailStart.

Recorre las tres capas y reporta cómo crece y se ordena la información:

    data_lake/raw/       → archivos landed por fecha de ingesta (trazabilidad)
    data_lake/processed/ → archivo maestro acumulativo de ventas (filas por día)
    Postgres (estrella)  → FactVentas agrupada por día / mes / año vía DimTiempo

Pensado como evidencia de "cargas incrementales": ejecutar antes y después de
cada lote para mostrar el crecimiento de la tabla de hechos.

Invocación (Docker):
    docker compose exec backend python manage.py audit_pipeline
"""

from collections import Counter
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand
from django.db.models import Count, Sum

from core.etl.ingest_transform import MASTER_VENTAS_NAME
from core.models import DimCanal, DimCliente, DimProducto, DimTiempo, FactVentas


class Command(BaseCommand):
    help = "Auditoría del pipeline: raw → processed (maestro) → FactVentas por día/mes/año."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--lake-root",
            default="/data_lake",
            help="Raíz del data lake (default: /data_lake en Docker).",
        )

    def handle(self, *args, **options) -> None:
        lake_root = Path(options["lake_root"])
        raw_dir = lake_root / "raw"
        processed_dir = lake_root / "processed"

        self.stdout.write(self.style.MIGRATE_HEADING("=== AUDITORÍA RetailStart — pipeline ==="))

        self._audit_raw(raw_dir)
        self._audit_master(processed_dir)
        self._audit_dw()

    def _audit_raw(self, raw_dir: Path) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("\n[1] Data Lake raw/ (landing por fecha)"))
        if not raw_dir.is_dir():
            self.stdout.write(self.style.WARNING(f"  (no existe {raw_dir})"))
            return
        files = sorted(p for p in raw_dir.iterdir() if p.is_file())
        if not files:
            self.stdout.write("  (sin archivos)")
            return
        for p in files:
            extra = ""
            if p.suffix == ".csv" and p.stem.startswith(("ventas_pos", "ventas_online")):
                try:
                    extra = f"  ({len(pd.read_csv(p))} filas)"
                except Exception:  # noqa: BLE001 - auditoría no debe romper por un CSV
                    extra = "  (no legible)"
            self.stdout.write(f"  - {p.name}{extra}")

    def _audit_master(self, processed_dir: Path) -> None:
        self.stdout.write(
            self.style.MIGRATE_HEADING("\n[2] Processed — maestro acumulativo de ventas")
        )
        master = processed_dir / MASTER_VENTAS_NAME
        if not master.is_file():
            self.stdout.write(
                self.style.WARNING(
                    f"  (no existe {master.name}; ejecuta run_etl --append-master)"
                )
            )
            return
        df = pd.read_csv(master, parse_dates=["fecha"])
        self.stdout.write(f"  Archivo: {master.name}")
        self.stdout.write(f"  Filas totales: {len(df)}")
        if not df.empty:
            fmin, fmax = df["fecha"].min(), df["fecha"].max()
            self.stdout.write(f"  Rango de fechas: {fmin.date()} … {fmax.date()}")
            por_dia = df.groupby(df["fecha"].dt.date).size()
            self.stdout.write("  Filas por día:")
            for dia, n in por_dia.items():
                self.stdout.write(f"    {dia}: {n}")

    def _audit_dw(self) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("\n[3] Data Warehouse (estrella Postgres)"))
        self.stdout.write(f"  DimCliente:  {DimCliente.objects.count()}")
        self.stdout.write(f"  DimProducto: {DimProducto.objects.count()}")
        self.stdout.write(f"  DimTiempo:   {DimTiempo.objects.count()}")
        self.stdout.write(f"  DimCanal:    {DimCanal.objects.count()}")
        self.stdout.write(f"  FactVentas:  {FactVentas.objects.count()}")

        if not FactVentas.objects.exists():
            self.stdout.write("  (FactVentas vacía)")
            return

        self.stdout.write("  Hechos por día:")
        por_dia = (
            FactVentas.objects.values("fecha__fecha_completa")
            .annotate(n=Count("id"), monto=Sum("monto"))
            .order_by("fecha__fecha_completa")
        )
        for row in por_dia:
            self.stdout.write(
                f"    {row['fecha__fecha_completa']}: {row['n']} hechos, "
                f"monto={row['monto']}"
            )

        self.stdout.write("  Hechos por mes (año-mes):")
        por_mes: Counter = Counter()
        montos_mes: Counter = Counter()
        for row in FactVentas.objects.values(
            "fecha__anio", "fecha__mes"
        ).annotate(n=Count("id"), monto=Sum("monto")):
            clave = f"{row['fecha__anio']}-{int(row['fecha__mes']):02d}"
            por_mes[clave] += row["n"]
            montos_mes[clave] += row["monto"] or 0
        for clave in sorted(por_mes):
            self.stdout.write(f"    {clave}: {por_mes[clave]} hechos, monto={montos_mes[clave]}")

        self.stdout.write("  Hechos por año:")
        por_anio = (
            FactVentas.objects.values("fecha__anio")
            .annotate(n=Count("id"), monto=Sum("monto"))
            .order_by("fecha__anio")
        )
        for row in por_anio:
            self.stdout.write(
                f"    {row['fecha__anio']}: {row['n']} hechos, monto={row['monto']}"
            )

        self.stdout.write("  Hechos por canal:")
        por_canal = (
            FactVentas.objects.values("canal__canal")
            .annotate(n=Count("id"), monto=Sum("monto"))
            .order_by("-monto")
        )
        for row in por_canal:
            self.stdout.write(
                f"    {row['canal__canal']}: {row['n']} hechos, monto={row['monto']}"
            )
