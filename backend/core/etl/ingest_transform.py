from __future__ import annotations

"""
ETL (batch) para Actividad 2 — capa *processed* del data lake.

Árbol de dependencias (dónde vive cada cosa):

    data_lake/raw/*.csv|json|xml|txt     ← salida de `run_elt_ingest` (ELT)
            │
            │  extract_from_lake()  lee el archivo *más reciente* por stem
            ▼
    ┌───────────────────────────────────────┐
    │  transform()  (pandas)                 │
    │  · limpia / dedup clientes y productos│
    │  · unifica ventas_pos + ventas_online │
    │  · enriquece (merge clientes/producto)│
    │  · agrega totales por cliente/canal/  │
    │    producto                           │
    └───────────────────────────────────────┘
            │
            │  load_to_processed()
            ▼
    data_lake/processed/<nombre>_<timestamp>.csv

Responsabilidad por etapa:
- Extract: leer fuentes heterogéneas desde `data_lake/raw/` (CSV/JSON/XML/TXT).
- Transform: limpieza mínima, unificación omnicanal (POS + online) y agregaciones base.
  Las ventas unificadas incluyen `fecha` más columnas de calendario (`anio`, `mes`, `dia`, `id_tiempo`)
  para trazabilidad con la dimensión tiempo del DW (`load_dw` + `DimTiempo`).
- Load (a archivos): escribir CSV procesados en `data_lake/processed/` con timestamp.

Invocación: `python manage.py run_etl` (Docker: `docker compose exec backend python manage.py run_etl`).
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class LakePaths:
    raw: Path
    processed: Path


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _latest_raw_sidecar(raw_dir: Path, stem: str, ext: str) -> Path:
    """
    Preferir última versión landed en raw: `{stem}_YYYYMMDD{ext}`, con fallback `{stem}{ext}`.
    """
    cand: list[Path] = list(raw_dir.glob(f"{stem}_*{ext}"))
    legacy = raw_dir / f"{stem}{ext}"
    if legacy.is_file():
        cand.append(legacy)
    if not cand:
        raise FileNotFoundError(
            f"ETL: no hay archivo en {raw_dir} para '{stem}' (esperaba {stem}_*{ext} o {stem}{ext})."
        )
    return max(cand, key=lambda p: p.stat().st_mtime)


def _read_json(path: Path) -> pd.DataFrame:
    data: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return pd.DataFrame(data)


def _read_xml_logistica(path: Path) -> pd.DataFrame:
    import xml.etree.ElementTree as ET

    root = ET.fromstring(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for pedido in root.findall("pedido"):
        rows.append(
            {
                "id": int(pedido.findtext("id", default="0")),
                "id_cliente": int(pedido.findtext("cliente", default="0")),
                "estado": pedido.findtext("estado", default=""),
            }
        )
    return pd.DataFrame(rows)


def _read_logs_txt(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ts_str, action, user = line[:19], line[20:].split(" ", 1)[0], line.split(" ", 2)[-1]
        rows.append({"timestamp": ts_str, "action": action, "raw": line, "user": user})
    return pd.DataFrame(rows)


def extract_from_lake(lake: LakePaths) -> dict[str, pd.DataFrame]:
    r = lake.raw
    return {
        "ventas_pos": _read_csv(_latest_raw_sidecar(r, "ventas_pos", ".csv")),
        "ventas_online": _read_csv(_latest_raw_sidecar(r, "ventas_online", ".csv")),
        "clientes": _read_csv(_latest_raw_sidecar(r, "clientes_crm", ".csv")),
        "productos": _read_csv(_latest_raw_sidecar(r, "productos_erp", ".csv")),
        "eventos_app": _read_json(_latest_raw_sidecar(r, "eventos_app", ".json")),
        "logistica": _read_xml_logistica(_latest_raw_sidecar(r, "logistica", ".xml")),
        "logs_sistema": _read_logs_txt(_latest_raw_sidecar(r, "logs_sistema", ".txt")),
    }


def transform(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    clientes = dfs["clientes"].copy()
    clientes["email"] = clientes["email"].astype(str).str.strip().str.lower()
    clientes = clientes.drop_duplicates(subset=["id_cliente"], keep="first")

    productos = dfs["productos"].copy()
    productos = productos.drop_duplicates(subset=["id_producto"], keep="first")

    ventas_pos = dfs["ventas_pos"].copy()
    ventas_pos["fecha"] = pd.to_datetime(ventas_pos["fecha"], errors="coerce")
    ventas_pos["cantidad"] = pd.to_numeric(ventas_pos["cantidad"], errors="coerce").fillna(0).astype(int)
    ventas_pos["precio_unitario"] = pd.to_numeric(ventas_pos["precio_unitario"], errors="coerce").fillna(0).astype(int)
    ventas_pos["monto"] = ventas_pos["cantidad"] * ventas_pos["precio_unitario"]
    ventas_pos["canal"] = "pos"

    ventas_online = dfs["ventas_online"].copy()
    ventas_online["fecha"] = pd.to_datetime(ventas_online["fecha"], errors="coerce")
    ventas_online["total"] = pd.to_numeric(ventas_online["total"], errors="coerce").fillna(0).astype(int)
    ventas_online["monto"] = ventas_online["total"]
    ventas_online["cantidad"] = 1
    ventas_online["precio_unitario"] = ventas_online["total"]
    ventas_online["id_producto"] = pd.NA
    ventas_online["tienda"] = pd.NA

    ventas_online = ventas_online.rename(columns={"id_orden": "id_venta"})

    ventas_online_norm = ventas_online.assign(
        precio_unitario=ventas_online["precio_unitario"],
        tienda=pd.NA,
    )[
        ["id_venta", "fecha", "id_cliente", "id_producto", "cantidad", "precio_unitario", "monto", "canal", "tienda"]
    ]

    ventas = pd.concat(
        [
            ventas_pos[
                ["id_venta", "fecha", "id_cliente", "id_producto", "cantidad", "precio_unitario", "monto", "canal", "tienda"]
            ],
            ventas_online_norm,
        ],
        ignore_index=True,
    )

    ventas = ventas.dropna(subset=["fecha", "id_cliente"])
    ventas["id_cliente"] = pd.to_numeric(ventas["id_cliente"], errors="coerce").astype("Int64")
    ventas["id_producto"] = pd.to_numeric(ventas["id_producto"], errors="coerce").astype("Int64")

    # Calendario explícito en CSV processed (alineado con DimTiempo.id_tiempo = YYYYMMDD en el DW).
    ventas["anio"] = ventas["fecha"].dt.year.astype("Int64")
    ventas["mes"] = ventas["fecha"].dt.month.astype("Int64")
    ventas["dia"] = ventas["fecha"].dt.day.astype("Int64")
    ventas["id_tiempo"] = (
        ventas["fecha"].dt.year * 10000 + ventas["fecha"].dt.month * 100 + ventas["fecha"].dt.day
    ).astype("Int64")

    # Dataset limpio para análisis: ventas + clientes + productos
    ventas_enriquecidas = (
        ventas.merge(clientes, on="id_cliente", how="left")
        .merge(productos, on="id_producto", how="left")
        .sort_values(["fecha", "id_venta"])
        .reset_index(drop=True)
    )

    # Tablas analíticas simples
    total_por_cliente = (
        ventas_enriquecidas.groupby(["id_cliente", "nombre", "apellido", "segmento"], dropna=False)["monto"]
        .sum()
        .reset_index()
        .sort_values("monto", ascending=False)
    )
    total_por_canal = ventas_enriquecidas.groupby(["canal"], dropna=False)["monto"].sum().reset_index().sort_values("monto", ascending=False)
    total_por_producto = (
        ventas_enriquecidas.groupby(["id_producto", "nombre_producto", "categoria"], dropna=False)["monto"]
        .sum()
        .reset_index()
        .sort_values("monto", ascending=False)
    )

    return {
        "clientes_limpio": clientes,
        "productos_limpio": productos,
        "ventas_unificadas": ventas,
        "ventas_enriquecidas": ventas_enriquecidas,
        "total_por_cliente": total_por_cliente,
        "total_por_canal": total_por_canal,
        "total_por_producto": total_por_producto,
        "eventos_app": dfs["eventos_app"],
        "logistica": dfs["logistica"],
        "logs_sistema": dfs["logs_sistema"],
    }


def load_to_processed(lake: LakePaths, transformed: dict[str, pd.DataFrame]) -> list[Path]:
    lake.processed.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_paths: list[Path] = []
    for name, df in transformed.items():
        out = lake.processed / f"{name}_{stamp}.csv"
        df.to_csv(out, index=False)
        out_paths.append(out)
    return out_paths


def run_pipeline(lake_root: Path) -> list[Path]:
    lake = LakePaths(raw=lake_root / "raw", processed=lake_root / "processed")
    dfs = extract_from_lake(lake)
    transformed = transform(dfs)
    return load_to_processed(lake, transformed)

