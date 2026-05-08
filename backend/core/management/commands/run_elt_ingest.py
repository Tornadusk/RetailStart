from __future__ import annotations

from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.etl.elt_ingest import DEFAULT_SCATTERED_SOURCES, ingest_scattered_sources


class Command(BaseCommand):
    """
    ELT — Extract + Load al Data Lake: copia datos sueltos desde carpetas heterogéneas
    a `data_lake/raw/` sin transformar. Los archivos destino llevan sufijo `_YYYYMMDD`.

    Por defecto lee desde `/data_sources` (Docker) o la ruta que pases con `--sources-root`.
    """

    help = "ELT: copy scattered source files into data_lake/raw/ (no transform)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--sources-root",
            default="/data_sources",
            help="Root folder containing scattered system folders (default: /data_sources in Docker).",
        )
        parser.add_argument(
            "--lake-root",
            default="/data_lake",
            help="Data lake raw/ parent folder (default: /data_lake).",
        )
        parser.add_argument(
            "--ingest-date",
            default="",
            help="Fecha AAAAMMDD o YYYY-MM-DD para el sufijo del nombre en raw (default: hoy).",
        )

    def handle(self, *args, **options):
        try:
            ingest_day = _parse_ingest_date(options["ingest_date"])
        except ValueError as e:
            raise CommandError(str(e)) from e
        sources_root = Path(options["sources_root"])
        lake_raw = Path(options["lake_root"]) / "raw"
        outputs = ingest_scattered_sources(
            sources_root, lake_raw, DEFAULT_SCATTERED_SOURCES, ingest_day=ingest_day
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"ELT ingest OK. Copied {len(outputs)} files to {lake_raw} "
                f"from {len(DEFAULT_SCATTERED_SOURCES)} dispersed paths under {sources_root}."
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
        y, mo, d = int(parts[0]), int(parts[1]), int(parts[2])
        return date(y, mo, d)
    if len(raw) == 8 and raw.isdigit():
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
    raise ValueError("Usa ingest-date como YYYY-MM-DD o AAAAMMDD.")
