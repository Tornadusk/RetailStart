from __future__ import annotations

"""
Genera datos realistas y ejecuta la pipeline completa para el Día 5 (2026-06-05).

Uso (Docker):
    docker compose exec backend python manage.py seed_day_5
    docker compose exec backend python manage.py seed_day_5 --skip-audit
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from core.management.commands._seed_helpers import run_day_pipeline


class Command(BaseCommand):
    help = "Genera datos y carga el pipeline completo para el Día 5 (2026-06-05)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--sources-root", default="/data_sources",
            help="Raíz de fuentes (default: /data_sources).",
        )
        parser.add_argument(
            "--lake-root", default="/data_lake",
            help="Raíz del data lake (default: /data_lake).",
        )
        parser.add_argument(
            "--skip-audit", action="store_true",
            help="No ejecutar audit_pipeline al final.",
        )

    def handle(self, *args, **options) -> None:
        run_day_pipeline(
            day=5,
            sources_root=Path(options["sources_root"]),
            lake_root=Path(options["lake_root"]),
            stdout=self.stdout,
            style=self.style,
            skip_audit=options["skip_audit"],
        )
