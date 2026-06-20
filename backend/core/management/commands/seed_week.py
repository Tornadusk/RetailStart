from __future__ import annotations

"""
Genera datos realistas y ejecuta la pipeline completa para los 5 días
(2026-06-01 a 2026-06-05) de forma secuencial e incremental.

Uso (Docker):
    docker compose exec backend python manage.py seed_week
    docker compose exec backend python manage.py seed_week --skip-audit
    docker compose exec backend python manage.py seed_week --audit-only-last

Cada día genera sus archivos fuente, los ingiere (ELT), transforma (ETL)
y carga al Data Warehouse de forma incremental. Al finalizar, el DW
contiene 5 días de datos con 25 clientes, 25 productos y 50 ventas
(5 POS + 5 online por día).
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from core.management.commands._seed_helpers import run_day_pipeline


class Command(BaseCommand):
    help = (
        "Genera datos y carga la pipeline para 5 días (2026-06-01 a 2026-06-05) "
        "de forma incremental."
    )

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
            help="No ejecutar audit_pipeline en ningún día.",
        )
        parser.add_argument(
            "--audit-only-last", action="store_true",
            help="Ejecutar audit_pipeline solo después del último día (más rápido).",
        )

    def handle(self, *args, **options) -> None:
        sources_root = Path(options["sources_root"])
        lake_root = Path(options["lake_root"])
        skip_all_audit = options["skip_audit"]
        audit_only_last = options["audit_only_last"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n╔══════════════════════════════════════════════════════════╗\n"
            "║  SEED WEEK — Carga de 5 días (2026-06-01 a 2026-06-05) ║\n"
            "╚══════════════════════════════════════════════════════════╝"
        ))

        for day in range(1, 6):
            if skip_all_audit:
                skip = True
            elif audit_only_last:
                skip = day < 5
            else:
                skip = False

            run_day_pipeline(
                day=day,
                sources_root=sources_root,
                lake_root=lake_root,
                stdout=self.stdout,
                style=self.style,
                skip_audit=skip,
            )

        self.stdout.write(self.style.SUCCESS(
            "\n══════════════════════════════════════════════════════════\n"
            "✓ SEED WEEK COMPLETADO — 5 días cargados exitosamente.\n"
            "  Fechas: 2026-06-01 a 2026-06-05\n"
            "  Clientes: 25 | Productos: 25 | Ventas: ~50\n"
            "══════════════════════════════════════════════════════════"
        ))
