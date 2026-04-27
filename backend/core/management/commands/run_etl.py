from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from core.etl.ingest_transform import run_pipeline


class Command(BaseCommand):
    """
    Entrada “operativa” del ETL.

    - Lee el Data Lake (carpetas) desde `--lake-root` (por defecto `/data_lake` en Docker)
    - Ejecuta `run_pipeline` y deja salidas CSV en `data_lake/processed/`
    """

    help = "Run ingestion + transform pipeline from data lake raw to processed CSVs."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--lake-root",
            default="/data_lake",
            help="Path to data lake root (default: /data_lake inside Docker).",
        )

    def handle(self, *args, **options):
        lake_root = Path(options["lake_root"])
        outputs = run_pipeline(lake_root=lake_root)
        self.stdout.write(self.style.SUCCESS(f"ETL OK. Wrote {len(outputs)} processed files."))
        for p in outputs:
            self.stdout.write(f"- {p}")

