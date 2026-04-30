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

        def _format_monto_ticks(ax, axis: str) -> None:
            # Evita notación científica 1e6 en ejes (se ve gigante/fea en thumbnails web).
            from matplotlib.ticker import FuncFormatter

            def fmt(v, _pos):
                try:
                    return f"${int(round(float(v))):,}".replace(",", ".")
                except Exception:
                    return f"{v}"

            if axis == "x":
                ax.xaxis.set_major_formatter(FuncFormatter(fmt))
            else:
                ax.yaxis.set_major_formatter(FuncFormatter(fmt))

        def hbar_chart(labels: list[str], values: list[int], title: str, filename: str) -> Path:
            # Barras horizontales: mejor lectura cuando los labels incluyen texto largo y se incrustan en dashboards/PDF.
            n = max(1, len(labels))
            height = min(10.5, max(3.6, 0.42 * n + 2.1))
            # Mantener PNG “web-friendly”: pocas pulgadas + DPI moderado.
            plt.figure(figsize=(6.2, height))
            y_pos = list(range(len(labels)))
            plt.barh(y_pos, values, color="#4aa3ff")
            plt.title(title, fontsize=11)
            plt.yticks(y_pos, labels, fontsize=8)
            plt.xlabel("Total monto", fontsize=9)
            ax = plt.gca()
            _format_monto_ticks(ax, "x")
            plt.grid(axis="x", linestyle="--", alpha=0.30)
            ax.invert_yaxis()
            plt.tick_params(axis="x", labelsize=8)
            plt.tight_layout(pad=0.6)
            path = out_dir / filename
            plt.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.10)
            plt.close()
            return path

        def vbar_chart(labels: list[str], values: list[int], title: str, filename: str) -> Path:
            plt.figure(figsize=(6.2, 3.5))
            plt.bar(labels, values, color="#4aa3ff")
            plt.title(title, fontsize=11)
            plt.xticks(rotation=0, fontsize=9)
            plt.ylabel("Total monto", fontsize=9)
            ax = plt.gca()
            _format_monto_ticks(ax, "y")
            plt.grid(axis="y", linestyle="--", alpha=0.30)
            plt.tick_params(axis="y", labelsize=8)
            plt.tight_layout(pad=0.6)
            path = out_dir / filename
            plt.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.10)
            plt.close()
            return path

        p1 = hbar_chart(
            [f'{r["cliente__id_cliente"]} {r["cliente__nombre"]}' for r in top_clientes],
            [int(r["total"] or 0) for r in top_clientes],
            "Mejores clientes (Top 10) - Total monto",
            "top_clientes.png",
        )

        # Canales típicamente son pocas etiquetas cortas → vertical suele funcionar mejor.
        p2 = vbar_chart(
            [r["canal__canal"] for r in top_canales],
            [int(r["total"] or 0) for r in top_canales],
            "Ventas por canal - Total monto",
            "ventas_por_canal.png",
        )

        # productos puede venir null (ventas online no tienen producto)
        prod_rows = [r for r in top_productos if r["producto__id_producto"] is not None]
        p3 = hbar_chart(
            [f'{r["producto__id_producto"]} {r["producto__nombre_producto"]}' for r in prod_rows],
            [int(r["total"] or 0) for r in prod_rows],
            "Productos con más ventas (Top 10) - Total monto",
            "top_productos.png",
        )

        self.stdout.write(self.style.SUCCESS("Analysis OK. Charts saved:"))
        for p in (p1, p2, p3):
            self.stdout.write(f"- {p}")

