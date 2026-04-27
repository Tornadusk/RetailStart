from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from django.core.management.base import BaseCommand
from django.db.models import Sum

from core.models import FactVentas


class Command(BaseCommand):
    """
    Capa de “consumo” (Actividad 2).

    Lee el DW (Postgres) y genera evidencia en PNG:
    - mejores clientes
    - ventas por canal
    - productos con más ventas
    """

    help = "Generate simple analysis charts from DW (top clients, channel, product)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--out-dir",
            default="/data_lake/processed/evidence",
            help="Output directory for charts (default: /data_lake/processed/evidence).",
        )

    def handle(self, *args, **options):
        out_dir = Path(options["out_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)

        top_clientes = (
            FactVentas.objects.values("cliente__id_cliente", "cliente__nombre", "cliente__apellido")
            .annotate(total=Sum("monto"))
            .order_by("-total")[:10]
        )
        top_canales = FactVentas.objects.values("canal__canal").annotate(total=Sum("monto")).order_by("-total")
        top_productos = (
            FactVentas.objects.values("producto__id_producto", "producto__nombre_producto")
            .annotate(total=Sum("monto"))
            .order_by("-total")[:10]
        )

        def bar_chart(labels, values, title, filename):
            plt.figure(figsize=(10, 5))
            plt.bar(labels, values)
            plt.title(title)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            path = out_dir / filename
            plt.savefig(path)
            plt.close()
            return path

        p1 = bar_chart(
            [f'{r["cliente__id_cliente"]} {r["cliente__nombre"]}' for r in top_clientes],
            [int(r["total"] or 0) for r in top_clientes],
            "Mejores clientes (Top 10) - total monto",
            "top_clientes.png",
        )

        p2 = bar_chart(
            [r["canal__canal"] for r in top_canales],
            [int(r["total"] or 0) for r in top_canales],
            "Ventas por canal - total monto",
            "ventas_por_canal.png",
        )

        # productos puede venir null (ventas online no tienen producto)
        prod_rows = [r for r in top_productos if r["producto__id_producto"] is not None]
        p3 = bar_chart(
            [f'{r["producto__id_producto"]} {r["producto__nombre_producto"]}' for r in prod_rows],
            [int(r["total"] or 0) for r in prod_rows],
            "Productos con más ventas (Top 10) - total monto",
            "top_productos.png",
        )

        self.stdout.write(self.style.SUCCESS("Analysis OK. Charts saved:"))
        for p in (p1, p2, p3):
            self.stdout.write(f"- {p}")

