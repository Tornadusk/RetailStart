"""
Tests del pipeline incremental (sin base de datos).

Validan la lógica clave de "cargas incrementales":
- el archivo maestro acumula lotes y deduplica ventas repetidas;
- la ingesta de un lote landa los archivos en raw/ con sufijo de fecha;
- la transformación unifica ventas POS + online y genera la clave de tiempo.

Se usan SimpleTestCase + carpetas temporales (no requieren Postgres).
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
from django.test import SimpleTestCase

from core.etl.elt_ingest import ingest_sales_batch
from core.etl.ingest_transform import (
    MASTER_VENTAS_NAME,
    append_to_master,
    transform,
)


def _ventas_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class AppendToMasterTests(SimpleTestCase):
    def test_acumula_y_deduplica(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            processed = Path(tmp)

            lote_1 = _ventas_df(
                [
                    {"id_venta": 1, "fecha": "2026-04-01", "canal": "pos", "monto": 100},
                    {"id_venta": 2, "fecha": "2026-04-02", "canal": "web", "monto": 200},
                ]
            )
            append_to_master(processed, lote_1)

            # Lote 2: una venta nueva + una repetida (misma id_venta+canal) con monto distinto.
            lote_2 = _ventas_df(
                [
                    {"id_venta": 2, "fecha": "2026-04-02", "canal": "web", "monto": 999},
                    {"id_venta": 3, "fecha": "2026-04-06", "canal": "pos", "monto": 300},
                ]
            )
            master_path = append_to_master(processed, lote_2)

            df = pd.read_csv(master_path)
            # 3 ventas únicas (1, 2, 3): la repetida no duplica filas.
            self.assertEqual(len(df), 3)
            self.assertEqual(sorted(df["id_venta"].tolist()), [1, 2, 3])
            # keep="last": la venta 2 conserva el monto del lote más reciente.
            monto_v2 = df.loc[df["id_venta"] == 2, "monto"].iloc[0]
            self.assertEqual(int(monto_v2), 999)

    def test_orden_cronologico(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            processed = Path(tmp)
            append_to_master(
                processed,
                _ventas_df(
                    [
                        {"id_venta": 9, "fecha": "2026-04-08", "canal": "pos", "monto": 1},
                        {"id_venta": 8, "fecha": "2026-04-01", "canal": "pos", "monto": 1},
                    ]
                ),
            )
            df = pd.read_csv(Path(tmp) / MASTER_VENTAS_NAME, parse_dates=["fecha"])
            fechas = df["fecha"].tolist()
            self.assertEqual(fechas, sorted(fechas))


class IngestSalesBatchTests(SimpleTestCase):
    def test_landa_con_sufijo_de_fecha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            batch = root / "lote_x"
            batch.mkdir()
            (batch / "ventas_pos.csv").write_text(
                "id_venta,fecha,id_cliente,id_producto,cantidad,precio_unitario,tienda\n"
                "1,2026-04-06,101,2001,1,1000,Santiago\n",
                encoding="utf-8",
            )
            (batch / "ventas_online.csv").write_text(
                "id_orden,fecha,id_cliente,total,canal\n5001,2026-04-06,101,1000,web\n",
                encoding="utf-8",
            )

            lake_raw = root / "raw"
            written = ingest_sales_batch(batch, lake_raw, ingest_day=date(2026, 4, 6))

            nombres = sorted(p.name for p in written)
            self.assertEqual(
                nombres, ["ventas_online_20260406.csv", "ventas_pos_20260406.csv"]
            )
            for p in written:
                self.assertTrue(p.is_file())

    def test_error_si_falta_archivo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            batch = Path(tmp) / "vacio"
            batch.mkdir()
            with self.assertRaises(FileNotFoundError):
                ingest_sales_batch(batch, Path(tmp) / "raw", ingest_day=date(2026, 4, 6))


class TransformTests(SimpleTestCase):
    def _dfs_minimos(self) -> dict[str, pd.DataFrame]:
        return {
            "clientes": pd.DataFrame(
                [
                    {
                        "id_cliente": 101,
                        "nombre": "Juan",
                        "apellido": "Perez",
                        "email": " JUAN@email.com ",
                        "segmento": "Premium",
                        "ciudad": "Santiago",
                    }
                ]
            ),
            "productos": pd.DataFrame(
                [
                    {
                        "id_producto": 2001,
                        "nombre_producto": "Notebook",
                        "categoria": "Tecnologia",
                        "precio_base": 140000,
                        "proveedor": "Lenovo",
                    }
                ]
            ),
            "ventas_pos": pd.DataFrame(
                [
                    {
                        "id_venta": 1,
                        "fecha": "2026-04-01",
                        "id_cliente": 101,
                        "id_producto": 2001,
                        "cantidad": 2,
                        "precio_unitario": 150000,
                        "tienda": "Santiago",
                    }
                ]
            ),
            "ventas_online": pd.DataFrame(
                [
                    {
                        "id_orden": 5001,
                        "fecha": "2026-04-02",
                        "id_cliente": 101,
                        "total": 300000,
                        "canal": "web",
                    }
                ]
            ),
            "eventos_app": pd.DataFrame([{"id_evento": 1, "id_cliente": 101}]),
            "logistica": pd.DataFrame([{"id": 1, "id_cliente": 101, "estado": "Enviado"}]),
            "logs_sistema": pd.DataFrame(
                [{"timestamp": "2026-04-01 10:00:00", "action": "LOGIN", "raw": "x", "user": "u"}]
            ),
            "callcenter": pd.DataFrame(
                [
                    {
                        "id_llamada": 1,
                        "id_cliente": 101,
                        "fecha": "2026-04-01",
                        "motivo": "Consulta",
                        "duracion": 5,
                    }
                ]
            ),
            "redes_sociales": pd.DataFrame(
                [{"usuario": "c1", "comentario": "ok", "rating": 5}]
            ),
            "proveedores": pd.DataFrame(
                [{"id_proveedor": 1, "nombre": "Lenovo", "producto": "Notebook", "precio": 140000}]
            ),
            "multimedia": pd.DataFrame(
                [{"id_producto": 2001, "tipo": "imagen", "archivo": "n.jpg"}]
            ),
        }

    def test_unifica_pos_y_online_con_id_tiempo(self) -> None:
        out = transform(self._dfs_minimos())
        ventas = out["ventas_unificadas"]

        self.assertEqual(len(ventas), 2)
        self.assertEqual(set(ventas["canal"]), {"pos", "web"})

        # id_tiempo = AAAAMMDD para enlazar con DimTiempo.
        pos = ventas[ventas["canal"] == "pos"].iloc[0]
        self.assertEqual(int(pos["id_tiempo"]), 20260401)
        self.assertEqual(int(pos["monto"]), 300000)  # 2 * 150000

    def test_email_normalizado(self) -> None:
        out = transform(self._dfs_minimos())
        email = out["clientes_limpio"]["email"].iloc[0]
        self.assertEqual(email, "juan@email.com")
