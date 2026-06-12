from __future__ import annotations

"""
Carga incremental de un día (rúbrica Evaluación — Parte 6).

Encadena en un solo comando lo que la demostración debe mostrar secuencialmente:
  fuentes (dia_1 / dia_2) → raw → processed (maestro) → DW → auditoría.

Ejemplo (Docker):
  python manage.py run_incremental_day --day dia_1 --ingest-date 2026-04-01
  python manage.py run_incremental_day --day dia_2 --ingest-date 2026-04-02
"""

from datetime import date
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from core.etl.elt_ingest import DEFAULT_SCATTERED_SOURCES, ingest_scattered_sources
from core.etl.ingest_transform import run_pipeline


class Command(BaseCommand):
    help = (
        "Carga incremental de un día: ELT → ETL (maestro) → load_dw (incremental) → audit_pipeline."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--day",
            required=True,
            help="Subcarpeta bajo data_sources con el lote del día (ej. dia_1, dia_2).",
        )
        parser.add_argument(
            "--sources-root",
            default="/data_sources",
            help="Raíz de fuentes (default: /data_sources).",
        )
        parser.add_argument(
            "--lake-root",
            default="/data_lake",
            help="Raíz del data lake (default: /data_lake).",
        )
        parser.add_argument(
            "--ingest-date",
            required=True,
            help="Fecha del lote YYYY-MM-DD o AAAAMMDD (sufijo en raw/).",
        )
        parser.add_argument(
            "--skip-audit",
            action="store_true",
            help="No ejecutar audit_pipeline al final.",
        )

    def handle(self, *args, **options) -> None:
        ingest_day = _parse_ingest_date(options["ingest_date"])
        if ingest_day is None:
            raise CommandError("--ingest-date es obligatorio (YYYY-MM-DD o AAAAMMDD).")

        day_folder = options["day"].strip()
        sources_root = Path(options["sources_root"]) / day_folder
        if not sources_root.is_dir():
            raise CommandError(
                f"No existe {sources_root}. Crea data_sources/{day_folder}/ con las fuentes del día."
            )

        lake_root = Path(options["lake_root"])
        lake_raw = lake_root / "raw"

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"=== Carga incremental: {day_folder} ({ingest_day.isoformat()}) ==="
            )
        )

        # 1) ELT → raw/
        written = ingest_scattered_sources(
            sources_root,
            lake_raw,
            DEFAULT_SCATTERED_SOURCES,
            ingest_day=ingest_day,
        )
        self.stdout.write(self.style.SUCCESS(f"[1/4] ELT: {len(written)} archivos en raw/"))
        for p in written:
            self.stdout.write(f"      - {p.name}")

        # 2) ETL → processed/ + maestro acumulativo
        outputs = run_pipeline(lake_root, append_master=True)
        self.stdout.write(
            self.style.SUCCESS(f"[2/4] ETL: {len(outputs)} salidas (incl. ventas_unificadas_maestro.csv)")
        )

        # 3) DW incremental
        call_command(
            "load_dw",
            processed_dir=str(lake_root / "processed"),
            incremental=True,
            ventas_file="maestro",
        )
        self.stdout.write(self.style.SUCCESS("[3/4] load_dw --incremental --ventas-file maestro"))

        # 4) Auditoría (evidencia rúbrica)
        if not options["skip_audit"]:
            self.stdout.write(self.style.MIGRATE_HEADING("[4/4] Auditoría"))
            call_command("audit_pipeline", lake_root=str(lake_root))

        self.stdout.write(
            self.style.SUCCESS(
                f"Carga de {day_folder} completada. Ejecuta audit_pipeline antes/después "
                "para evidencia en el informe."
            )
        )


def _parse_ingest_date(raw: str) -> date | None:
    raw = raw.strip()
    if not raw:
        return None
    if "-" in raw:
        parts = raw.split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    if len(raw) == 8 and raw.isdigit():
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
    raise CommandError("Usa --ingest-date como YYYY-MM-DD o AAAAMMDD.")
