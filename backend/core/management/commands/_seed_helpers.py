"""
Helpers compartidos para los comandos seed_day_N y seed_week.

Genera archivos de datos realistas (CSV, JSON, XML, TXT) para cada día,
siguiendo la misma estructura de carpetas que dia_1 / dia_2 pero con
fechas 2026-06-XX e IDs únicos por día.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# ── Configuración global ──────────────────────────────────────────────
BASE_DATE_PREFIX = "2026-06-"

_PER_DAY = 5  # registros por día

# ── IDs codificados por fecha (Opción 2) ─────────────────────────────
# Formato: prefijo + MM + DD + correlativo(2 dígitos)
# Ejemplo para 2026-06-01:
#   POS online:    60101, 60102, 60103, 60104, 60105
#   Marketplace:  560101, 560102, ...   (prefijo 5)
#   Llamadas:     760101, 760102, ...   (prefijo 7)
#   Eventos:      860101, 860102, ...   (prefijo 8)
#   Pedidos:      960101, 960102, ...   (prefijo 9)
# Todos caben en IntegerField (max ~2.1 mil millones).
# Nunca colisionan entre días ni entre tipos de transacción.
_MES = 6  # Junio


def _id_venta_pos(day: int, i: int) -> int:
    """ID único de venta POS: 6MMDD{i+1:02d} — ej. 60101 para 2026-06-01, registro 1."""
    return int(f"{_MES:02d}{day:02d}{i + 1:02d}")


def _id_orden_online(day: int, i: int) -> int:
    """ID único de orden online: 56MMDD{i+1:02d} — ej. 560101."""
    return int(f"5{_MES:02d}{day:02d}{i + 1:02d}")


def _id_llamada(day: int, i: int) -> int:
    """ID único de llamada: 76MMDD{i+1:02d} — ej. 760101."""
    return int(f"7{_MES:02d}{day:02d}{i + 1:02d}")


def _id_evento(day: int, i: int) -> int:
    """ID único de evento app: 86MMDD{i+1:02d} — ej. 860101."""
    return int(f"8{_MES:02d}{day:02d}{i + 1:02d}")


def _id_pedido(day: int, i: int) -> int:
    """ID único de pedido logística: 96MMDD{i+1:02d} — ej. 960101."""
    return int(f"9{_MES:02d}{day:02d}{i + 1:02d}")

# ── Datos realistas por día (5 días × 5 registros) ───────────────────

CLIENTES_POR_DIA: dict[int, list[dict]] = {
    1: [
        {"id_cliente": 101, "nombre": "Juan", "apellido": "Perez", "email": "juan@email.com", "segmento": "Premium", "ciudad": "Santiago"},
        {"id_cliente": 102, "nombre": "Ana", "apellido": "Gomez", "email": "ana@email.com", "segmento": "Regular", "ciudad": "Valparaiso"},
        {"id_cliente": 103, "nombre": "Carlos", "apellido": "Rojas", "email": "carlos@email.com", "segmento": "Premium", "ciudad": "Concepcion"},
        {"id_cliente": 104, "nombre": "Maria", "apellido": "Lopez", "email": "maria@email.com", "segmento": "Nuevo", "ciudad": "Santiago"},
        {"id_cliente": 105, "nombre": "Pedro", "apellido": "Diaz", "email": "pedro@email.com", "segmento": "Regular", "ciudad": "Temuco"},
    ],
    2: [
        {"id_cliente": 106, "nombre": "Laura", "apellido": "Soto", "email": "laura@email.com", "segmento": "Premium", "ciudad": "Antofagasta"},
        {"id_cliente": 107, "nombre": "Diego", "apellido": "Muñoz", "email": "diego@email.com", "segmento": "Regular", "ciudad": "Santiago"},
        {"id_cliente": 108, "nombre": "Camila", "apellido": "Herrera", "email": "camila@email.com", "segmento": "Nuevo", "ciudad": "Rancagua"},
        {"id_cliente": 109, "nombre": "Andres", "apellido": "Morales", "email": "andres@email.com", "segmento": "Premium", "ciudad": "Valparaiso"},
        {"id_cliente": 110, "nombre": "Sofia", "apellido": "Castillo", "email": "sofia@email.com", "segmento": "Regular", "ciudad": "Concepcion"},
    ],
    3: [
        {"id_cliente": 111, "nombre": "Felipe", "apellido": "Vargas", "email": "felipe@email.com", "segmento": "Premium", "ciudad": "Santiago"},
        {"id_cliente": 112, "nombre": "Valentina", "apellido": "Reyes", "email": "valentina@email.com", "segmento": "Nuevo", "ciudad": "Temuco"},
        {"id_cliente": 113, "nombre": "Matias", "apellido": "Contreras", "email": "matias@email.com", "segmento": "Regular", "ciudad": "Valdivia"},
        {"id_cliente": 114, "nombre": "Isidora", "apellido": "Fuentes", "email": "isidora@email.com", "segmento": "Premium", "ciudad": "La Serena"},
        {"id_cliente": 115, "nombre": "Sebastian", "apellido": "Tapia", "email": "sebastian@email.com", "segmento": "Regular", "ciudad": "Arica"},
    ],
    4: [
        {"id_cliente": 116, "nombre": "Francisca", "apellido": "Navarro", "email": "francisca@email.com", "segmento": "Nuevo", "ciudad": "Iquique"},
        {"id_cliente": 117, "nombre": "Tomas", "apellido": "Bravo", "email": "tomas@email.com", "segmento": "Premium", "ciudad": "Santiago"},
        {"id_cliente": 118, "nombre": "Catalina", "apellido": "Pino", "email": "catalina@email.com", "segmento": "Regular", "ciudad": "Osorno"},
        {"id_cliente": 119, "nombre": "Nicolas", "apellido": "Vera", "email": "nicolas@email.com", "segmento": "Premium", "ciudad": "Talca"},
        {"id_cliente": 120, "nombre": "Javiera", "apellido": "Espinoza", "email": "javiera@email.com", "segmento": "Regular", "ciudad": "Chillan"},
    ],
    5: [
        {"id_cliente": 121, "nombre": "Ignacio", "apellido": "Aravena", "email": "ignacio@email.com", "segmento": "Premium", "ciudad": "Copiapo"},
        {"id_cliente": 122, "nombre": "Antonia", "apellido": "Gutierrez", "email": "antonia@email.com", "segmento": "Nuevo", "ciudad": "Santiago"},
        {"id_cliente": 123, "nombre": "Benjamin", "apellido": "Salazar", "email": "benjamin@email.com", "segmento": "Regular", "ciudad": "Valparaiso"},
        {"id_cliente": 124, "nombre": "Constanza", "apellido": "Rios", "email": "constanza@email.com", "segmento": "Premium", "ciudad": "Concepcion"},
        {"id_cliente": 125, "nombre": "Martin", "apellido": "Campos", "email": "martin@email.com", "segmento": "Regular", "ciudad": "Puerto Montt"},
    ],
}

PRODUCTOS_POR_DIA: dict[int, list[dict]] = {
    1: [
        {"id_producto": 2001, "nombre_producto": "Notebook Lenovo", "categoria": "Tecnologia", "precio_base": 140000, "proveedor": "Lenovo"},
        {"id_producto": 2002, "nombre_producto": "Smartphone Samsung", "categoria": "Tecnologia", "precio_base": 280000, "proveedor": "Samsung"},
        {"id_producto": 2003, "nombre_producto": "Polera Hombre", "categoria": "Vestuario", "precio_base": 30000, "proveedor": "Nike"},
        {"id_producto": 2004, "nombre_producto": "Silla Oficina", "categoria": "Hogar", "precio_base": 15000, "proveedor": "Ikea"},
        {"id_producto": 2005, "nombre_producto": "Audifonos Sony", "categoria": "Tecnologia", "precio_base": 70000, "proveedor": "Sony"},
    ],
    2: [
        {"id_producto": 2006, "nombre_producto": "Monitor LG", "categoria": "Tecnologia", "precio_base": 120000, "proveedor": "LG"},
        {"id_producto": 2007, "nombre_producto": "Teclado Mecanico", "categoria": "Tecnologia", "precio_base": 50000, "proveedor": "Logitech"},
        {"id_producto": 2008, "nombre_producto": "Zapatillas Running", "categoria": "Vestuario", "precio_base": 80000, "proveedor": "Adidas"},
        {"id_producto": 2009, "nombre_producto": "Lampara LED", "categoria": "Hogar", "precio_base": 25000, "proveedor": "Philips"},
        {"id_producto": 2010, "nombre_producto": "Mouse Gamer", "categoria": "Tecnologia", "precio_base": 35000, "proveedor": "Razer"},
    ],
    3: [
        {"id_producto": 2011, "nombre_producto": "Tablet iPad", "categoria": "Tecnologia", "precio_base": 350000, "proveedor": "Apple"},
        {"id_producto": 2012, "nombre_producto": "Chaqueta Outdoor", "categoria": "Vestuario", "precio_base": 95000, "proveedor": "NorthFace"},
        {"id_producto": 2013, "nombre_producto": "Aspiradora Robot", "categoria": "Hogar", "precio_base": 180000, "proveedor": "iRobot"},
        {"id_producto": 2014, "nombre_producto": "Parlante Bluetooth", "categoria": "Tecnologia", "precio_base": 45000, "proveedor": "JBL"},
        {"id_producto": 2015, "nombre_producto": "Reloj Smartwatch", "categoria": "Tecnologia", "precio_base": 200000, "proveedor": "Garmin"},
    ],
    4: [
        {"id_producto": 2016, "nombre_producto": "Impresora HP", "categoria": "Tecnologia", "precio_base": 90000, "proveedor": "HP"},
        {"id_producto": 2017, "nombre_producto": "Camiseta Deportiva", "categoria": "Vestuario", "precio_base": 25000, "proveedor": "Puma"},
        {"id_producto": 2018, "nombre_producto": "Cafetera Express", "categoria": "Hogar", "precio_base": 150000, "proveedor": "DeLonghi"},
        {"id_producto": 2019, "nombre_producto": "Webcam HD", "categoria": "Tecnologia", "precio_base": 60000, "proveedor": "Logitech"},
        {"id_producto": 2020, "nombre_producto": "Mochila Laptop", "categoria": "Vestuario", "precio_base": 45000, "proveedor": "Samsonite"},
    ],
    5: [
        {"id_producto": 2021, "nombre_producto": "SSD 1TB", "categoria": "Tecnologia", "precio_base": 75000, "proveedor": "Samsung"},
        {"id_producto": 2022, "nombre_producto": "Pantalon Jeans", "categoria": "Vestuario", "precio_base": 40000, "proveedor": "Levis"},
        {"id_producto": 2023, "nombre_producto": "Ventilador Torre", "categoria": "Hogar", "precio_base": 55000, "proveedor": "Bionaire"},
        {"id_producto": 2024, "nombre_producto": "Pendrive 128GB", "categoria": "Tecnologia", "precio_base": 15000, "proveedor": "Kingston"},
        {"id_producto": 2025, "nombre_producto": "Manta Polar", "categoria": "Hogar", "precio_base": 20000, "proveedor": "Cannon"},
    ],
}

TIENDAS = ["Santiago", "Providencia", "Maipu", "La Florida", "Puente Alto",
           "Ñuñoa", "Las Condes", "Vitacura", "San Bernardo", "Quilicura"]

CANALES_ONLINE = ["web", "app"]

MOTIVOS_CALL = ["Consulta", "Reclamo", "Soporte", "Devolucion", "Consulta"]

TIPOS_EVENTO = ["click", "busqueda", "click", "compra", "click"]

ESTADOS_LOGISTICA = ["Enviado", "Entregado", "Pendiente", "En tránsito", "Entregado"]

COMENTARIOS_REDES = [
    ("Buen producto", 5), ("Mala calidad", 2), ("Excelente servicio", 5),
    ("Envio rapido", 4), ("Recomendado", 5), ("Precio justo", 4),
    ("Demora en envio", 3), ("Calidad superior", 5), ("Buena atencion", 4),
    ("Podria mejorar", 3),
]


def _date_str(day: int) -> str:
    """Retorna '2026-06-01', '2026-06-02', etc."""
    return f"{BASE_DATE_PREFIX}{day:02d}"


def generate_day_sources(day: int, sources_root: Path) -> Path:
    """
    Genera la carpeta data_sources/dia_{day} con 11 archivos fuente
    realistas, usando fecha 2026-06-{day:02d} e IDs únicos.

    Retorna el path de la carpeta creada.
    """
    if day < 1 or day > 5:
        raise ValueError(f"day debe estar entre 1 y 5, recibido: {day}")

    fecha = _date_str(day)
    day_dir = sources_root / f"dia_{day}"

    clientes = CLIENTES_POR_DIA[day]
    productos = PRODUCTOS_POR_DIA[day]

    # Índice global en las listas de precios/cantidades (0-based, por día)
    v_offset = (day - 1) * _PER_DAY

    # ── 1) crm_export/clientes_crm.csv ──
    _mkdir(day_dir / "crm_export")
    _write_csv(
        day_dir / "crm_export" / "clientes_crm.csv",
        ["id_cliente", "nombre", "apellido", "email", "segmento", "ciudad"],
        [
            [c["id_cliente"], c["nombre"], c["apellido"], c["email"], c["segmento"], c["ciudad"]]
            for c in clientes
        ],
    )

    # ── 2) crm_export/callcenter.csv ──
    _write_csv(
        day_dir / "crm_export" / "callcenter.csv",
        ["id_llamada", "id_cliente", "fecha", "motivo", "duracion"],
        [
            [_id_llamada(day, i), clientes[i]["id_cliente"], fecha, MOTIVOS_CALL[i], (i + 1) * 3]
            for i in range(_PER_DAY)
        ],
    )

    # ── 3) erp_snapshot/productos_erp.csv ──
    _mkdir(day_dir / "erp_snapshot")
    _write_csv(
        day_dir / "erp_snapshot" / "productos_erp.csv",
        ["id_producto", "nombre_producto", "categoria", "precio_base", "proveedor"],
        [
            [p["id_producto"], p["nombre_producto"], p["categoria"], p["precio_base"], p["proveedor"]]
            for p in productos
        ],
    )

    # ── 4) erp_snapshot/proveedores.csv ──
    _write_csv(
        day_dir / "erp_snapshot" / "proveedores.csv",
        ["id_proveedor", "nombre", "producto", "precio"],
        [
            [i + 1 + (day - 1) * _PER_DAY, p["proveedor"], p["nombre_producto"].split()[0], p["precio_base"]]
            for i, p in enumerate(productos)
        ],
    )

    # ── 5) sistemas_legacy/pos/ventas_pos.csv ──
    _mkdir(day_dir / "sistemas_legacy" / "pos")
    precios_pos = [150000, 300000, 50000, 20000, 80000,
                   120000, 50000, 80000, 120000, 25000,
                   350000, 95000, 180000, 45000, 200000,
                   90000, 25000, 150000, 60000, 45000,
                   75000, 40000, 55000, 15000, 20000]
    cantidades_pos = [2, 1, 1, 3, 1, 1, 2, 1, 1, 3, 1, 2, 1, 3, 1, 2, 1, 1, 2, 1, 3, 1, 2, 1, 1]
    tiendas = TIENDAS[(day - 1) * 2: (day - 1) * 2 + 5]
    if len(tiendas) < 5:
        tiendas = (tiendas + TIENDAS)[:5]

    _write_csv(
        day_dir / "sistemas_legacy" / "pos" / "ventas_pos.csv",
        ["id_venta", "fecha", "id_cliente", "id_producto", "cantidad", "precio_unitario", "tienda"],
        [
            [
                _id_venta_pos(day, i),
                fecha,
                clientes[i]["id_cliente"],
                productos[i]["id_producto"],
                cantidades_pos[v_offset + i],
                precios_pos[v_offset + i],
                tiendas[i],
            ]
            for i in range(_PER_DAY)
        ],
    )

    # ── 6) marketplace/ventas_online.csv ──
    _mkdir(day_dir / "marketplace")
    totales_online = [300000, 50000, 60000, 300000, 80000,
                      80000, 100000, 120000, 150000, 25000,
                      400000, 70000, 200000, 90000, 250000,
                      100000, 45000, 180000, 75000, 55000,
                      80000, 60000, 70000, 20000, 35000]
    _write_csv(
        day_dir / "marketplace" / "ventas_online.csv",
        ["id_orden", "fecha", "id_cliente", "total", "canal"],
        [
            [
                _id_orden_online(day, i),
                fecha,
                clientes[i]["id_cliente"],
                totales_online[v_offset + i],
                CANALES_ONLINE[i % 2],
            ]
            for i in range(_PER_DAY)
        ],
    )

    # ── 7) mobile_analytics/eventos_app.json ──
    _mkdir(day_dir / "mobile_analytics")
    eventos = [
        {
            "id_evento": _id_evento(day, i),
            "id_cliente": clientes[i]["id_cliente"],
            "tipo": TIPOS_EVENTO[i],
            "producto": productos[i]["id_producto"],
        }
        for i in range(_PER_DAY)
    ]
    (day_dir / "mobile_analytics" / "eventos_app.json").write_text(
        json.dumps(eventos, indent=0, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # ── 8) sistemas_legacy/proveedor_logistica/logistica.xml ──
    _mkdir(day_dir / "sistemas_legacy" / "proveedor_logistica")
    pedidos_xml = ["<pedidos>"]
    for i in range(_PER_DAY):
        ped_id = _id_pedido(day, i)
        cli_id = clientes[i]["id_cliente"]
        estado = ESTADOS_LOGISTICA[i]
        pedidos_xml.append(
            f"  <pedido><id>{ped_id}</id><cliente>{cli_id}</cliente><estado>{estado}</estado></pedido>"
        )
    pedidos_xml.append("</pedidos>")
    (day_dir / "sistemas_legacy" / "proveedor_logistica" / "logistica.xml").write_text(
        "\n".join(pedidos_xml) + "\n", encoding="utf-8"
    )

    # ── 9) infra_logs/logs_sistema.txt ──
    _mkdir(day_dir / "infra_logs")
    base_hour = 10
    logs = [
        f"{fecha} {base_hour}:00:01 LOGIN user{clientes[0]['id_cliente']}",
        f"{fecha} {base_hour}:05:10 VIEW_PRODUCT {productos[0]['id_producto']}",
        f"{fecha} {base_hour}:06:30 LOGOUT user{clientes[0]['id_cliente']}",
        f"{fecha} {base_hour + 1}:00:00 LOGIN user{clientes[1]['id_cliente']}",
        f"{fecha} {base_hour + 1}:10:22 ERROR sistema_pago",
    ]
    (day_dir / "infra_logs" / "logs_sistema.txt").write_text(
        "\n".join(logs) + "\n", encoding="utf-8"
    )

    # ── 10) marketing_analytics/redes_sociales.json ──
    _mkdir(day_dir / "marketing_analytics")
    redes = [
        {
            "usuario": f"cliente{i + 1 + (day - 1) * _PER_DAY}",
            "comentario": COMENTARIOS_REDES[(day - 1) * _PER_DAY + i][0]
            if (day - 1) * _PER_DAY + i < len(COMENTARIOS_REDES)
            else "Buen producto",
            "rating": COMENTARIOS_REDES[(day - 1) * _PER_DAY + i][1]
            if (day - 1) * _PER_DAY + i < len(COMENTARIOS_REDES)
            else 4,
        }
        for i in range(_PER_DAY)
    ]
    (day_dir / "marketing_analytics" / "redes_sociales.json").write_text(
        json.dumps(redes, indent=0, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # ── 11) catalogo_multimedia/multimedia.csv ──
    _mkdir(day_dir / "catalogo_multimedia")
    tipos_media = ["imagen", "imagen", "imagen", "imagen", "video"]
    _write_csv(
        day_dir / "catalogo_multimedia" / "multimedia.csv",
        ["id_producto", "tipo", "archivo"],
        [
            [
                productos[i]["id_producto"],
                tipos_media[i],
                f"{productos[i]['nombre_producto'].split()[0].lower()}.{'mp4' if tipos_media[i] == 'video' else 'jpg'}",
            ]
            for i in range(_PER_DAY)
        ],
    )

    return day_dir


def run_day_pipeline(day: int, sources_root: Path, lake_root: Path, stdout, style, *, skip_audit: bool = False) -> None:
    """
    Ejecuta la pipeline completa para un día:
      1) Genera archivos fuente en data_sources/dia_{day}
      2) ELT → raw/
      3) ETL → processed/ + maestro
      4) load_dw incremental
      5) audit_pipeline (opcional)
    """
    from datetime import date as _date

    from django.core.management import call_command

    from core.etl.elt_ingest import DEFAULT_SCATTERED_SOURCES, ingest_scattered_sources
    from core.etl.ingest_transform import run_pipeline

    fecha = _date_str(day)
    ingest_day = _date(2026, 6, day)
    day_folder = f"dia_{day}"

    stdout.write(style.MIGRATE_HEADING(
        f"\n{'='*60}\n=== Día {day}: {fecha} ({day_folder}) ===\n{'='*60}"
    ))

    # 0) Generar archivos fuente
    day_dir = generate_day_sources(day, sources_root)
    stdout.write(style.SUCCESS(f"[0/4] Datos fuente generados en {day_dir}"))

    day_source = sources_root / day_folder
    lake_raw = lake_root / "raw"

    # 1) ELT → raw/
    written = ingest_scattered_sources(
        day_source, lake_raw, DEFAULT_SCATTERED_SOURCES, ingest_day=ingest_day,
    )
    stdout.write(style.SUCCESS(f"[1/4] ELT: {len(written)} archivos en raw/"))
    for p in written:
        stdout.write(f"      - {p.name}")

    # 2) ETL → processed/ + maestro acumulativo
    outputs = run_pipeline(lake_root, append_master=True)
    stdout.write(style.SUCCESS(
        f"[2/4] ETL: {len(outputs)} salidas (incl. ventas_unificadas_maestro.csv)"
    ))

    # 3) DW incremental
    call_command(
        "load_dw",
        processed_dir=str(lake_root / "processed"),
        incremental=True,
        ventas_file="maestro",
    )
    stdout.write(style.SUCCESS("[3/4] load_dw --incremental --ventas-file maestro"))

    # 4) Auditoría
    if not skip_audit:
        stdout.write(style.MIGRATE_HEADING("[4/4] Auditoría"))
        call_command("audit_pipeline", lake_root=str(lake_root))

    stdout.write(style.SUCCESS(f"✓ Carga del {day_folder} ({fecha}) completada.\n"))


# ── Utilidades internas ───────────────────────────────────────────────

def _mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_csv(path: Path, headers: list[str], rows: list[list]) -> None:
    lines = [",".join(str(h) for h in headers)]
    for row in rows:
        lines.append(",".join(str(v) for v in row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
