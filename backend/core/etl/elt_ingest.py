from __future__ import annotations

"""
ELT — fase Extract + Load hacia el Data Lake (sin transformar).

Simula sistemas heterogéneos: cada fuente vive en su propia carpeta bajo `data_sources/`.
Este módulo solo copia los archivos “tal cual” a `data_lake/raw/` con los nombres que
consume el pipeline batch (`run_etl`).

La fase Transform en un ELT puro suele ejecutarse después en el almacén (SQL, dbt, etc.).
Aquí la transformación analítica sigue en Python vía `ingest_transform.run_pipeline` tras
tener todo consolidado en `raw`.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceFile:
    """Ruta relativa bajo `sources_root` → nombre final en `data_lake/raw/`."""

    relative_path: str
    lake_raw_name: str


# Orígenes dispersos (carpetas distintas) → un solo landing zone `raw/`
DEFAULT_SCATTERED_SOURCES: tuple[SourceFile, ...] = (
    SourceFile("sistemas_legacy/pos/ventas_pos.csv", "ventas_pos.csv"),
    SourceFile("marketplace/ventas_online.csv", "ventas_online.csv"),
    SourceFile("crm_export/clientes_crm.csv", "clientes_crm.csv"),
    SourceFile("erp_snapshot/productos_erp.csv", "productos_erp.csv"),
    SourceFile("mobile_analytics/eventos_app.json", "eventos_app.json"),
    SourceFile("proveedor_logistica/logistica.xml", "logistica.xml"),
    SourceFile("infra_logs/logs_sistema.txt", "logs_sistema.txt"),
)


def ingest_scattered_sources(
    sources_root: Path,
    lake_raw: Path,
    sources: tuple[SourceFile, ...] = DEFAULT_SCATTERED_SOURCES,
) -> list[Path]:
    """
    Copia archivos desde múltiples carpetas hacia `lake_raw` sin modificar contenido.

    Returns
    -------
    list[Path]
        Rutas escritas en el data lake (raw).
    """
    lake_raw.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for spec in sources:
        src = sources_root / spec.relative_path
        if not src.is_file():
            raise FileNotFoundError(
                f"ELT ingest: no existe la fuente esperada: {src} "
                f"(¿existe la carpeta y los archivos del anexo bajo {sources_root!r}?)"
            )
        dest = lake_raw / spec.lake_raw_name
        shutil.copy2(src, dest)
        written.append(dest)
    return written
