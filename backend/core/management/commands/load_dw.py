from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.dw_calendar import fecha_a_id_tiempo, seed_dim_tiempo_calendar
from core.etl.ingest_transform import MASTER_VENTAS_NAME
from core.models import DimCanal, DimCliente, DimProducto, DimTiempo, FactVentas


@dataclass(frozen=True)
class ProcessedFiles:
    clientes: Path
    productos: Path
    ventas: Path


def _latest_processed(processed_dir: Path, prefix: str) -> Path:
    # Excluir el maestro acumulativo: se selecciona aparte con --ventas-file maestro.
    candidates = sorted(
        p
        for p in processed_dir.glob(f"{prefix}_*.csv")
        if p.name != MASTER_VENTAS_NAME
    )
    if not candidates:
        raise FileNotFoundError(f"No processed files found for prefix '{prefix}' in {processed_dir}")
    return candidates[-1]


def _resolve_ventas_file(processed_dir: Path, choice: str) -> Path:
    """`auto` = último snapshot; `maestro` = archivo acumulativo; o ruta explícita."""
    choice = (choice or "auto").strip()
    if choice == "maestro":
        master = processed_dir / MASTER_VENTAS_NAME
        if not master.is_file():
            raise FileNotFoundError(
                f"No existe {master}. Ejecuta antes: run_etl --append-master."
            )
        return master
    if choice not in ("auto", ""):
        p = Path(choice)
        if not p.is_file():
            raise FileNotFoundError(f"Archivo de ventas no encontrado: {p}")
        return p
    return _latest_processed(processed_dir, "ventas_unificadas")


def _pick_files(processed_dir: Path, ventas_choice: str = "auto") -> ProcessedFiles:
    return ProcessedFiles(
        clientes=_latest_processed(processed_dir, "clientes_limpio"),
        productos=_latest_processed(processed_dir, "productos_limpio"),
        ventas=_resolve_ventas_file(processed_dir, ventas_choice),
    )


class Command(BaseCommand):
    """
    Carga el Data Warehouse (Postgres) con un esquema en estrella.

    Fuente: últimos CSV del directorio `data_lake/processed/`.
    Destino: tablas del modelo estrella en `core.models`:
    - DimCliente, DimProducto, DimTiempo, DimCanal
    - FactVentas
    """

    help = "Load star schema tables (Postgres DW) from latest processed CSVs."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--processed-dir",
            default="/data_lake/processed",
            help="Processed directory (default: /data_lake/processed inside Docker).",
        )
        parser.add_argument(
            "--calendar-from",
            type=int,
            default=2020,
            help="Año inicial (inclusive) para pre-generar DimTiempo (default: 2020).",
        )
        parser.add_argument(
            "--calendar-to",
            type=int,
            default=2030,
            help="Año final (inclusive) para pre-generar DimTiempo (default: 2030).",
        )
        parser.add_argument(
            "--incremental",
            action="store_true",
            help=(
                "Upsert de hechos por (id_venta_origen, canal) sin borrar FactVentas. "
                "Suma lotes nuevos conservando la historia previa."
            ),
        )
        parser.add_argument(
            "--ventas-file",
            default="auto",
            help=(
                "Origen de ventas processed: 'auto' (último snapshot, default), "
                "'maestro' (ventas_unificadas_maestro.csv) o una ruta CSV explícita."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        processed_dir = Path(options["processed_dir"])
        y0 = int(options["calendar_from"])
        y1 = int(options["calendar_to"])
        if y0 > y1:
            raise CommandError("calendar-from debe ser <= calendar-to.")

        ncal = seed_dim_tiempo_calendar(y0, y1)
        self.stdout.write(
            f"DimTiempo calendario: intento de carga de {ncal} días ({y0}–{y1}), "
            f"filas en tabla: {DimTiempo.objects.count()}"
        )

        incremental = bool(options["incremental"])
        files = _pick_files(processed_dir, ventas_choice=options["ventas_file"])
        self.stdout.write(f"Ventas processed: {files.ventas.name} (incremental={incremental})")

        clientes = pd.read_csv(files.clientes)
        productos = pd.read_csv(files.productos)
        ventas = pd.read_csv(files.ventas, parse_dates=["fecha"])

        # Dimensions
        for _, r in clientes.iterrows():
            DimCliente.objects.update_or_create(
                id_cliente=int(r["id_cliente"]),
                defaults={
                    "nombre": str(r.get("nombre", "")),
                    "apellido": str(r.get("apellido", "")),
                    "email": str(r.get("email", "")),
                    "segmento": str(r.get("segmento", "")),
                    "ciudad": str(r.get("ciudad", "")),
                },
            )

        for _, r in productos.iterrows():
            DimProducto.objects.update_or_create(
                id_producto=int(r["id_producto"]),
                defaults={
                    "nombre_producto": str(r.get("nombre_producto", "")),
                    "categoria": str(r.get("categoria", "")),
                    "precio_base": int(r.get("precio_base", 0)),
                    "proveedor": str(r.get("proveedor", "")),
                },
            )

        # Canal dim
        for c in sorted(set(ventas["canal"].dropna().astype(str))):
            DimCanal.objects.update_or_create(canal=c)

        # Facts: full reload (delete + bulk) o incremental (upsert por venta+canal).
        if not incremental:
            FactVentas.objects.all().delete()

        tiempo_by_id = {t.id_tiempo: t for t in DimTiempo.objects.all()}
        canal_by_name = {c.canal: c for c in DimCanal.objects.all()}
        cliente_by_id = {c.id_cliente: c for c in DimCliente.objects.all()}
        producto_by_id = {p.id_producto: p for p in DimProducto.objects.all()}

        facts: list[FactVentas] = []
        n_nuevos = 0
        n_actualizados = 0
        for _, r in ventas.iterrows():
            fecha_dt = r["fecha"]
            if pd.isna(fecha_dt):
                continue
            f = fecha_dt.date()
            id_tiempo = fecha_a_id_tiempo(f)
            if id_tiempo not in tiempo_by_id:
                raise CommandError(
                    f"Fecha {f} fuera del calendario DimTiempo ({y0}–{y1}). "
                    "Amplía --calendar-from/--calendar-to o corrige fechas en ventas."
                )
            id_cliente = int(r["id_cliente"])
            canal = str(r["canal"])

            id_producto_val = r.get("id_producto")
            producto = None
            if not pd.isna(id_producto_val):
                producto = producto_by_id.get(int(id_producto_val))

            campos = {
                "fecha": tiempo_by_id[id_tiempo],
                "cliente": cliente_by_id[id_cliente],
                "producto": producto,
                "cantidad": int(r.get("cantidad", 0)),
                "precio_unitario": int(r.get("precio_unitario", 0)),
                "monto": int(r.get("monto", 0)),
            }

            if incremental:
                # Clave de negocio: misma venta de origen en el mismo canal = mismo hecho.
                _, created = FactVentas.objects.update_or_create(
                    id_venta_origen=int(r["id_venta"]),
                    canal=canal_by_name[canal],
                    defaults=campos,
                )
                if created:
                    n_nuevos += 1
                else:
                    n_actualizados += 1
            else:
                facts.append(
                    FactVentas(
                        id_venta_origen=int(r["id_venta"]),
                        canal=canal_by_name[canal],
                        **campos,
                    )
                )

        if not incremental:
            FactVentas.objects.bulk_create(facts, batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f"DW load OK (full reload: {len(facts)} hechos)."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DW load OK (incremental: {n_nuevos} nuevos, {n_actualizados} actualizados)."
                )
            )
        self.stdout.write(f"- DimCliente: {DimCliente.objects.count()}")
        self.stdout.write(f"- DimProducto: {DimProducto.objects.count()}")
        self.stdout.write(f"- DimTiempo: {DimTiempo.objects.count()}")
        self.stdout.write(f"- DimCanal: {DimCanal.objects.count()}")
        self.stdout.write(f"- FactVentas: {FactVentas.objects.count()}")

