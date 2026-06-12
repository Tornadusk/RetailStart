from __future__ import annotations

from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.etl.elt_ingest import SALES_BATCH_FILES, ingest_sales_batch


class Command(BaseCommand):
    """
    Ingiere un lote de ventas nuevas (un día / una semana) al Data Lake raw/.

    Simula la llegada de datos frescos para una carga incremental: solo copia los
    archivos de ventas (POS + online) de la carpeta del lote, con sufijo de fecha.
    Las dimensiones (clientes, productos) ya deben estar en raw/ (run_elt_ingest).

    Ejemplo (Docker):
        python manage.py ingest_sales_batch --batch lote_2 --ingest-date 2026-04-08
        python manage.py run_etl --append-master
        python manage.py load_dw --incremental --ventas-file maestro
    """

    help = "Ingesta incremental: copia ventas de un lote a data_lake/raw/ con fecha."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--batch",
            required=True,
            help="Nombre de la carpeta del lote (dentro de --batches-root). Ej: lote_2.",
        )
        parser.add_argument(
            "--batches-root",
            default="/data_sources/simulacion_semana",
            help="Carpeta que contiene los lotes (default: /data_sources/simulacion_semana).",
        )
        parser.add_argument(
            "--lake-root",
            default="/data_lake",
            help="Raíz del data lake (default: /data_lake).",
        )
        parser.add_argument(
            "--ingest-date",
            default="",
            help="Fecha AAAAMMDD o YYYY-MM-DD para el sufijo en raw (default: hoy).",
        )

    def handle(self, *args, **options) -> None:
        try:
            ingest_day = _parse_ingest_date(options["ingest_date"])
        except ValueError as e:
            raise CommandError(str(e)) from e

        batch_dir = Path(options["batches_root"]) / options["batch"]
        if not batch_dir.is_dir():
            raise CommandError(f"No existe la carpeta del lote: {batch_dir}")

        lake_raw = Path(options["lake_root"]) / "raw"
        try:
            outputs = ingest_sales_batch(
                batch_dir, lake_raw, SALES_BATCH_FILES, ingest_day=ingest_day
            )
        except FileNotFoundError as e:
            raise CommandError(str(e)) from e

        self.stdout.write(
            self.style.SUCCESS(
                f"Lote '{options['batch']}' ingerido: {len(outputs)} archivos a {lake_raw}."
            )
        )
        for p in outputs:
            self.stdout.write(f"- {p.name}")


def _parse_ingest_date(raw: str) -> date | None:
    raw = raw.strip()
    if not raw:
        return None
    if "-" in raw:
        parts = raw.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    if len(raw) == 8 and raw.isdigit():
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
    raise ValueError("Usa ingest-date como YYYY-MM-DD o AAAAMMDD.")
