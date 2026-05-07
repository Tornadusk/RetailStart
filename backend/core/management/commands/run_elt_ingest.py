from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from core.etl.elt_ingest import DEFAULT_SCATTERED_SOURCES, ingest_scattered_sources


class Command(BaseCommand):
    """
    ELT — Extract + Load al Data Lake: copia datos sueltos desde carpetas heterogéneas
    a `data_lake/raw/` sin transformar.

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
            help="Data lake root containing raw/ (default: /data_lake).",
        )

    def handle(self, *args, **options):
        sources_root = Path(options["sources_root"])
        lake_raw = Path(options["lake_root"]) / "raw"
        outputs = ingest_scattered_sources(sources_root, lake_raw, DEFAULT_SCATTERED_SOURCES)
        self.stdout.write(
            self.style.SUCCESS(
                f"ELT ingest OK. Copied {len(outputs)} files to {lake_raw} "
                f"from {len(DEFAULT_SCATTERED_SOURCES)} dispersed paths under {sources_root}."
            )
        )
        for p in outputs:
            self.stdout.write(f"- {p.name}")
