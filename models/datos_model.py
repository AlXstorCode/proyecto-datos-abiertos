import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()


def obtener_conexion():
    """Crea y devuelve una conexión activa a SQL Server usando variables de .env."""
    server = os.getenv("DB_SERVER", "localhost")
    database = os.getenv("DB_NAME", "DatosAbiertosDB")
    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    trusted = os.getenv("DB_TRUSTED", "yes").strip().lower()

    if trusted in ("yes", "true", "1"):
        cadena = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
    else:
        user = os.getenv("DB_USER", "")
        password = os.getenv("DB_PASSWORD", "")
        cadena = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )

    return pyodbc.connect(cadena)


def _a_entero_o_none(valor):
    """Convierte un valor a int de forma segura; devuelve None si está vacío o no es numérico."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if texto == "":
        return None
    try:
        return int(float(texto))
    except (ValueError, TypeError):
        return None


def contar_registros():
    """Devuelve cuántos registros existen actualmente en RegistrosAPI."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM RegistrosAPI")
        fila = cursor.fetchone()
        return int(fila[0]) if fila else 0
    finally:
        cursor.close()
        conexion.close()


def obtener_resumen():
    """Devuelve el total de registros y la suma del trafico prepago y pospago."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*), 
            COALESCE(SUM(trafico_prepago), 0),
            COALESCE(SUM(trafico_pospago), 0)
            FROM RegistrosAPI
        """)
        fila = cursor.fetchone()
        return {
            "total": fila[0],
            "suma_prepago": fila[1],
            "suma_pospago": fila[2],
        }
    finally:
        cursor.close()
        conexion.close()


def guardar_registros(datos):
    """Inserta solo los registros nuevos sin borrar la tabla, evitando N consultas 1 a 1."""
    if not datos:
        return 0

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    sql_existentes = """
        SELECT
            COALESCE(CAST(anno AS NVARCHAR(50)), ''),
            COALESCE(CAST(trimestre AS NVARCHAR(50)), ''),
            COALESCE(CAST(proveedor AS NVARCHAR(255)), ''),
            COALESCE(CAST(proveedor_destino AS NVARCHAR(255)), '')
        FROM RegistrosAPI
    """

    sql_insertar = """
        INSERT INTO RegistrosAPI (
            anno,
            trimestre,
            proveedor,
            proveedor_destino,
            trafico_prepago,
            trafico_pospago
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """

    try:
        cursor.execute(sql_existentes)
        existentes = {
            (str(r[0]), str(r[1]), str(r[2]), str(r[3]))
            for r in cursor.fetchall()
        }

        nuevas_filas = []
        for item in datos:
            anno = _a_entero_o_none(item.get("anno"))
            trimestre = _a_entero_o_none(item.get("trimestre"))
            proveedor = item.get("proveedor")
            proveedor_destino = item.get("proveedor_destino")
            trafico_prepago = _a_entero_o_none(item.get("trafico_prepago"))
            trafico_pospago = _a_entero_o_none(item.get("trafico_pospago"))

            clave = (
                "" if anno is None else str(anno),
                "" if trimestre is None else str(trimestre),
                "" if proveedor is None else str(proveedor),
                "" if proveedor_destino is None else str(proveedor_destino),
            )

            if clave not in existentes:
                existentes.add(clave)
                nuevas_filas.append((
                    anno,
                    trimestre,
                    proveedor,
                    proveedor_destino,
                    trafico_prepago,
                    trafico_pospago,
                ))

        if nuevas_filas:
            cursor.fast_executemany = True
            cursor.executemany(sql_insertar, nuevas_filas)

        conexion.commit()
        return len(nuevas_filas)
    except Exception:
        conexion.rollback()
        raise
    finally:
        cursor.close()
        conexion.close()


def sincronizar_si_es_necesario(cliente, minimo_registros=100, limite_descarga=None):
    """
    Revisa si la tabla tiene menos de 'minimo_registros' (por defecto 100).
    Si tiene menos de 100 (incluyendo 0), descarga de la API y guarda en SQL Server.
    """
    total_actual = contar_registros()
    if total_actual < minimo_registros:
        limite_efectivo = limite_descarga if limite_descarga is not None else cliente.limite
        datos = cliente.obtener_registros(limite=limite_efectivo)
        guardar_registros(datos)
        return True
    return False


def consultar_registros(filtros=None):
    """Consulta los registros en SQL Server aplicando filtros individuales por columna."""
    filtros = filtros or {}
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    columnas_permitidas = {
        "anno": "NVARCHAR(50)",
        "trimestre": "NVARCHAR(50)",
        "proveedor": "NVARCHAR(255)",
        "proveedor_destino": "NVARCHAR(255)",
        "trafico_prepago": "NVARCHAR(100)",
        "trafico_pospago": "NVARCHAR(100)",
    }

    condiciones = []
    parametros = []

    for col, tipo_texto in columnas_permitidas.items():
        valor = (filtros.get(col) or "").strip()
        if valor:
            condiciones.append(f"COALESCE(CAST({col} AS {tipo_texto}), '') LIKE ?")
            parametros.append(f"%{valor}%")

    sql = """
        SELECT
            anno,
            trimestre,
            proveedor,
            proveedor_destino,
            trafico_prepago,
            trafico_pospago
        FROM RegistrosAPI
    """
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    
    sql += " ORDER BY anno DESC, trimestre DESC, proveedor, proveedor_destino"

    try:
        cursor.execute(sql, parametros)
        columnas = [col[0] for col in cursor.description]
        filas = cursor.fetchall()
        return [dict(zip(columnas, fila)) for fila in filas]
    finally:
        cursor.close()
        conexion.close()