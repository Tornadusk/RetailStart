from __future__ import annotations

"""
ELT — fase Extract + Load hacia el Data Lake (sin transformar).

Simula sistemas heterogéneos: cada fuente vive en su propia carpeta bajo `data_sources/`.
Este módulo copia los archivos sin transformar contenido; el nombre en `raw/` lleva sufijo
`_YYYYMMDD` (fecha de ingesta) para trazabilidad y auditoría.

La fase Transform en un ELT puro suele ejecutarse después en el almacén (SQL, dbt, etc.).
Aquí la transformación analítica sigue en Python vía `ingest_transform.run_pipeline` tras
tener todo consolidado en `raw`.
"""

import shutil
from dataclasses import dataclass
from datetime import date
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
    SourceFile("sistemas_legacy/proveedor_logistica/logistica.xml", "logistica.xml"),
    SourceFile("infra_logs/logs_sistema.txt", "logs_sistema.txt"),
    SourceFile("crm_export/callcenter.csv", "callcenter.csv"),
    SourceFile("marketing_analytics/redes_sociales.json", "redes_sociales.json"),
    SourceFile("erp_snapshot/proveedores.csv", "proveedores.csv"),
    SourceFile("catalogo_multimedia/multimedia.csv", "multimedia.csv"),
)


def _dated_filename(lake_raw_name: str, ingest_stamp: str) -> str:
    """`ventas_pos.csv` → `ventas_pos_20260508.csv` con sufijo AAAAMMDD."""
    p = Path(lake_raw_name)
    return f"{p.stem}_{ingest_stamp}{p.suffix}"


def ingest_scattered_sources(
    sources_root: Path,
    lake_raw: Path,
    sources: tuple[SourceFile, ...] = DEFAULT_SCATTERED_SOURCES,
    ingest_day: date | None = None,
) -> list[Path]:
    """
    Copia archivos desde múltiples carpetas hacia `lake_raw` sin modificar contenido.

    Returns
    -------
    list[Path]
        Rutas escritas en el data lake (raw).
    """
    when = ingest_day or date.today()
    ingest_stamp = when.strftime("%Y%m%d")

    lake_raw.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for spec in sources:
        src = sources_root / spec.relative_path
        if not src.is_file():
            raise FileNotFoundError(
                f"ELT ingest: no existe la fuente esperada: {src} "
                f"(¿existe la carpeta y los archivos del anexo bajo {sources_root!r}?)"
            )
        dest = lake_raw / _dated_filename(spec.lake_raw_name, ingest_stamp)
        shutil.copy2(src, dest)
        written.append(dest)
    return written
