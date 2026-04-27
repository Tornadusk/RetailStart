from django.db import models


class DimCliente(models.Model):
    id_cliente = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField()
    segmento = models.CharField(max_length=50)
    ciudad = models.CharField(max_length=100)

    def __str__(self) -> str:
        return f"{self.id_cliente} - {self.nombre} {self.apellido}"


class DimProducto(models.Model):
    id_producto = models.IntegerField(unique=True)
    nombre_producto = models.CharField(max_length=200)
    categoria = models.CharField(max_length=100)
    precio_base = models.IntegerField()
    proveedor = models.CharField(max_length=100)

    def __str__(self) -> str:
        return f"{self.id_producto} - {self.nombre_producto}"


class DimTiempo(models.Model):
    fecha = models.DateField(unique=True)
    anio = models.IntegerField()
    mes = models.IntegerField()
    dia = models.IntegerField()

    def __str__(self) -> str:
        return self.fecha.isoformat()


class DimCanal(models.Model):
    canal = models.CharField(max_length=30, unique=True)

    def __str__(self) -> str:
        return self.canal


class FactVentas(models.Model):
    id_venta_origen = models.IntegerField()
    fecha = models.ForeignKey(DimTiempo, on_delete=models.PROTECT)
    cliente = models.ForeignKey(DimCliente, on_delete=models.PROTECT)
    producto = models.ForeignKey(DimProducto, on_delete=models.PROTECT, null=True, blank=True)
    canal = models.ForeignKey(DimCanal, on_delete=models.PROTECT)

    cantidad = models.IntegerField()
    precio_unitario = models.IntegerField()
    monto = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "fecha"]),
            models.Index(fields=["canal", "fecha"]),
            models.Index(fields=["producto", "fecha"]),
        ]

    def __str__(self) -> str:
        return f"venta {self.id_venta_origen} - {self.monto}"
