import pandas as pd
from sqlalchemy import create_engine, text
import os
from datetime import datetime


def conectar_db():
    usuario = "root"
    contrasena = "root"
    host = "localhost"
    puerto = 3306
    nombre_bd = "biblioteca_dw"

    engine_tmp = create_engine(
        f"mysql+pymysql://{usuario}:{contrasena}@{host}:{puerto}"
    )
    with engine_tmp.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {nombre_bd}"))
        conn.commit()

    engine = create_engine(
        f"mysql+pymysql://{usuario}:{contrasena}@{host}:{puerto}/{nombre_bd}"
    )
    return engine


def extraer_datos(ruta_csv):
    df = pd.read_csv(ruta_csv)
    return df


def limpiar_datos(df):
    df = df.copy()

    df.columns = df.columns.str.strip().str.lower()

    columnas_texto = ["alumno", "carrera", "libro", "categoria", "sede"]
    for col in columnas_texto:
        df[col] = df[col].str.strip()

    df["fecha_prestamo"] = pd.to_datetime(df["fecha_prestamo"])

    columnas_numericas = ["dias_prestamo", "multa_diaria", "total_multa"]
    for col in columnas_numericas:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def validar_datos(df, archivo_origen):
    errores = []
    validos = []
    ids_vistos = set()

    for i, fila in df.iterrows():
        id_prestamo = fila["id_prestamo"]
        datos_str = ",".join(str(fila[col]) for col in df.columns)
        fila_csv = i + 2

        total_esperado = fila["dias_prestamo"] * fila["multa_diaria"]
        if fila["total_multa"] != total_esperado:
            errores.append({
                "fecha_error": datetime.now(),
                "archivo_origen": archivo_origen,
                "fila_csv": fila_csv,
                "id_registro": id_prestamo,
                "descripcion_error": "total_multa incorrecto",
                "datos_originales": datos_str
            })
            continue

        if id_prestamo in ids_vistos:
            errores.append({
                "fecha_error": datetime.now(),
                "archivo_origen": archivo_origen,
                "fila_csv": fila_csv,
                "id_registro": id_prestamo,
                "descripcion_error": "id_prestamo duplicado",
                "datos_originales": datos_str
            })
            continue

        ids_vistos.add(id_prestamo)
        validos.append(fila)

    df_validos = pd.DataFrame(validos)
    return df_validos, errores


def crear_tablas(engine):
    tablas = [
        """CREATE TABLE IF NOT EXISTS dim_alumno (
            id_alumno INT AUTO_INCREMENT PRIMARY KEY,
            alumno VARCHAR(100) UNIQUE
        )""",
        """CREATE TABLE IF NOT EXISTS dim_carrera (
            id_carrera INT AUTO_INCREMENT PRIMARY KEY,
            carrera VARCHAR(100) UNIQUE
        )""",
        """CREATE TABLE IF NOT EXISTS dim_libro (
            id_libro INT AUTO_INCREMENT PRIMARY KEY,
            libro VARCHAR(200),
            categoria VARCHAR(100),
            UNIQUE(libro, categoria)
        )""",
        """CREATE TABLE IF NOT EXISTS dim_sede (
            id_sede INT AUTO_INCREMENT PRIMARY KEY,
            sede VARCHAR(100) UNIQUE
        )""",
        """CREATE TABLE IF NOT EXISTS dim_fecha (
            id_fecha INT PRIMARY KEY,
            fecha DATE UNIQUE,
            anio INT,
            mes INT,
            dia INT
        )""",
        """CREATE TABLE IF NOT EXISTS fact_prestamos (
            id_prestamo INT PRIMARY KEY,
            id_fecha INT,
            id_alumno INT,
            id_carrera INT,
            id_libro INT,
            id_sede INT,
            dias_prestamo INT,
            multa_diaria DECIMAL(10,2),
            total_multa DECIMAL(10,2),
            FOREIGN KEY (id_fecha) REFERENCES dim_fecha(id_fecha),
            FOREIGN KEY (id_alumno) REFERENCES dim_alumno(id_alumno),
            FOREIGN KEY (id_carrera) REFERENCES dim_carrera(id_carrera),
            FOREIGN KEY (id_libro) REFERENCES dim_libro(id_libro),
            FOREIGN KEY (id_sede) REFERENCES dim_sede(id_sede)
        )""",
        """CREATE TABLE IF NOT EXISTS etl_errores (
            id_error INT AUTO_INCREMENT PRIMARY KEY,
            fecha_error DATETIME NOT NULL,
            archivo_origen VARCHAR(255) NOT NULL,
            fila_csv INT,
            id_registro INT,
            descripcion_error VARCHAR(255) NOT NULL,
            datos_originales TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS etl_log (
            id_log INT AUTO_INCREMENT PRIMARY KEY,
            fecha_ejecucion DATETIME NOT NULL,
            archivo_origen VARCHAR(255) NOT NULL,
            filas_leidas INT NOT NULL,
            filas_cargadas INT NOT NULL,
            filas_rechazadas INT NOT NULL,
            estado VARCHAR(30) NOT NULL
        )"""
    ]

    with engine.connect() as conn:
        for sql in tablas:
            conn.execute(text(sql))
        conn.commit()


def limpiar_tablas(engine):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM fact_prestamos"))
        conn.execute(text("DELETE FROM dim_alumno"))
        conn.execute(text("DELETE FROM dim_carrera"))
        conn.execute(text("DELETE FROM dim_libro"))
        conn.execute(text("DELETE FROM dim_sede"))
        conn.execute(text("DELETE FROM dim_fecha"))
        conn.execute(text("DELETE FROM etl_errores"))
        conn.commit()


def cargar_dimensiones(engine, df):
    pass


def cargar_hechos(engine, df):
    pass


def registrar_errores(engine, errores):
    pass


def registrar_log(engine, resumen):
    pass


def generar_reporte(resumen):
    pass


def main():
    ruta_csv = os.path.join("data", "prestamos_biblioteca_100.csv")

    print("=" * 60)
    print("FASE 4 - EXTRACCIÓN Y LIMPIEZA")
    print("=" * 60)

    df_crudo = extraer_datos(ruta_csv)

    print("\n--- DATOS CRUDOS ---")
    print(f"Dimensiones: {df_crudo.shape}")
    print(f"\nColumnas: {list(df_crudo.columns)}")
    print(f"\nTipos de datos:\n{df_crudo.dtypes}")
    print(f"\nPrimeras 3 filas:\n{df_crudo.head(3)}")
    print(f"\nValores nulos:\n{df_crudo.isnull().sum()}")

    df_limpio = limpiar_datos(df_crudo)

    print("\n--- DATOS LIMPIOS ---")
    print(f"Dimensiones: {df_limpio.shape}")
    print(f"\nColumnas: {list(df_limpio.columns)}")
    print(f"\nTipos de datos:\n{df_limpio.dtypes}")
    print(f"\nPrimeras 3 filas:\n{df_limpio.head(3)}")
    print(f"\nValores nulos:\n{df_limpio.isnull().sum()}")

    print("\n" + "=" * 60)
    print("FASE 5 - CONEXION A MySQL Y CREACION DEL DW")
    print("=" * 60)

    engine = conectar_db()
    print("\n[OK] Conexion exitosa a MySQL")

    crear_tablas(engine)
    print("[OK] Tablas creadas / verificadas correctamente")

    limpiar_tablas(engine)
    print("[OK] Tablas limpiadas correctamente")

    with engine.connect() as conn:
        resultado = conn.execute(text("SHOW TABLES"))
        tablas = [fila[0] for fila in resultado]
        print(f"\nTablas en biblioteca_dw: {tablas}")

    print("\n" + "=" * 60)
    print("FASE 6 - VALIDACIONES DEL ETL")
    print("=" * 60)

    archivo = os.path.basename(ruta_csv)
    df_validos, errores = validar_datos(df_limpio, archivo)

    total_leidas = len(df_limpio)
    total_cargadas = len(df_validos)
    total_rechazadas = len(errores)

    print(f"\nFilas leidas: {total_leidas}")
    print(f"Filas cargadas: {total_cargadas}")
    print(f"Filas rechazadas: {total_rechazadas}")

    print(f"\n--- ERRORES DETECTADOS ({len(errores)}) ---")
    for e in errores:
        print(f"  Fila CSV {e['fila_csv']}: {e['descripcion_error']} (id: {e['id_registro']})")


if __name__ == "__main__":
    main()
