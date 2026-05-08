import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(name="FactVentas"),
        migrations.DeleteModel(name="DimTiempo"),
        migrations.CreateModel(
            name="DimTiempo",
            fields=[
                ("id_tiempo", models.IntegerField(primary_key=True, serialize=False)),
                ("fecha_completa", models.DateField(db_index=True, unique=True)),
                ("dia_semana", models.IntegerField()),
                ("nombre_dia", models.CharField(max_length=12)),
                ("dia_mes", models.IntegerField()),
                ("mes", models.IntegerField()),
                ("nombre_mes", models.CharField(max_length=16)),
                ("trimestre", models.IntegerField()),
                ("anio", models.IntegerField()),
                ("es_fin_semana", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="FactVentas",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("id_venta_origen", models.IntegerField()),
                ("cantidad", models.IntegerField()),
                ("precio_unitario", models.IntegerField()),
                ("monto", models.IntegerField()),
                ("canal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.dimcanal")),
                ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.dimcliente")),
                (
                    "fecha",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.dimtiempo"),
                ),
                (
                    "producto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="core.dimproducto",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["cliente", "fecha"], name="core_factve_cliente_cca6ee_idx"),
                    models.Index(fields=["canal", "fecha"], name="core_factve_canal_i_fa3e0a_idx"),
                    models.Index(fields=["producto", "fecha"], name="core_factve_product_881732_idx"),
                ],
            },
        ),
    ]
