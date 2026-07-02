from __future__ import annotations

"""
seed_day_6 — Genera y carga el Día 6 (2026-06-06).
Incluye 5 ventas POS y 5 online (10 transacciones).
"""

from pathlib import Path
from django.core.management.base import BaseCommand
from ._seed_helpers import run_day_pipeline

class Command(BaseCommand):
    help = "Genera y procesa el Día 6 (2026-06-06) completo (ELT -> ETL -> DW incremental)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--skip-audit", action="store_true")
        parser.add_argument("--skip-generate", action="store_true")

    def handle(self, *args, **options) -> None:
        sources_root = Path("/data_sources")
        lake_root = Path("/data_lake")
        run_day_pipeline(
            6,
            sources_root,
            lake_root,
            self.stdout,
            self.style,
            skip_audit=options["skip_audit"],
            skip_generate=options["skip_generate"],
        )
