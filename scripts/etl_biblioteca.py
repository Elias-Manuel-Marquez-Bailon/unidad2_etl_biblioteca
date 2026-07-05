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
    dim_alumno = df[["alumno"]].drop_duplicates()
    dim_carrera = df[["carrera"]].drop_duplicates()
    dim_libro = df[["libro", "categoria"]].drop_duplicates()
    dim_sede = df[["sede"]].drop_duplicates()
    dim_fecha = df[["fecha_prestamo"]].drop_duplicates().copy()
    dim_fecha.columns = ["fecha"]
    dim_fecha["anio"] = dim_fecha["fecha"].dt.year
    dim_fecha["mes"] = dim_fecha["fecha"].dt.month
    dim_fecha["dia"] = dim_fecha["fecha"].dt.day
    dim_fecha["id_fecha"] = dim_fecha["fecha"].dt.strftime("%Y%m%d").astype(int)

    with engine.connect() as conn:
        for _, fila in dim_alumno.iterrows():
            conn.execute(
                text("INSERT IGNORE INTO dim_alumno (alumno) VALUES (:alumno)"),
                {"alumno": fila["alumno"]}
            )
        for _, fila in dim_carrera.iterrows():
            conn.execute(
                text("INSERT IGNORE INTO dim_carrera (carrera) VALUES (:carrera)"),
                {"carrera": fila["carrera"]}
            )
        for _, fila in dim_libro.iterrows():
            conn.execute(
                text("INSERT IGNORE INTO dim_libro (libro, categoria) VALUES (:libro, :categoria)"),
                {"libro": fila["libro"], "categoria": fila["categoria"]}
            )
        for _, fila in dim_sede.iterrows():
            conn.execute(
                text("INSERT IGNORE INTO dim_sede (sede) VALUES (:sede)"),
                {"sede": fila["sede"]}
            )
        for _, fila in dim_fecha.iterrows():
            conn.execute(
                text("INSERT IGNORE INTO dim_fecha (id_fecha, fecha, anio, mes, dia) VALUES (:id, :fecha, :anio, :mes, :dia)"),
                {
                    "id": int(fila["id_fecha"]),
                    "fecha": fila["fecha"].date(),
                    "anio": int(fila["anio"]),
                    "mes": int(fila["mes"]),
                    "dia": int(fila["dia"])
                }
            )
        conn.commit()


def cargar_hechos(engine, df_validos):
    with engine.connect() as conn:
        dim_alumno_sql = pd.read_sql("SELECT id_alumno, alumno FROM dim_alumno", conn)
        dim_carrera_sql = pd.read_sql("SELECT id_carrera, carrera FROM dim_carrera", conn)
        dim_libro_sql = pd.read_sql("SELECT id_libro, libro, categoria FROM dim_libro", conn)
        dim_sede_sql = pd.read_sql("SELECT id_sede, sede FROM dim_sede", conn)

    dic_alumno = dict(zip(dim_alumno_sql["alumno"], dim_alumno_sql["id_alumno"]))
    dic_carrera = dict(zip(dim_carrera_sql["carrera"], dim_carrera_sql["id_carrera"]))
    dic_libro = dict(zip(zip(dim_libro_sql["libro"], dim_libro_sql["categoria"]), dim_libro_sql["id_libro"]))
    dic_sede = dict(zip(dim_sede_sql["sede"], dim_sede_sql["id_sede"]))

    df = df_validos.copy()
    df["id_alumno"] = df["alumno"].map(dic_alumno)
    df["id_carrera"] = df["carrera"].map(dic_carrera)
    df["id_libro"] = df[["libro", "categoria"]].apply(tuple, axis=1).map(dic_libro)
    df["id_sede"] = df["sede"].map(dic_sede)
    df["id_fecha"] = df["fecha_prestamo"].dt.strftime("%Y%m%d").astype(int)

    fact_prestamos = df[[
        "id_prestamo", "id_fecha", "id_alumno", "id_carrera",
        "id_libro", "id_sede", "dias_prestamo", "multa_diaria", "total_multa"
    ]]

    with engine.connect() as conn:
        for _, fila in fact_prestamos.iterrows():
            conn.execute(
                text("""INSERT INTO fact_prestamos
                    (id_prestamo, id_fecha, id_alumno, id_carrera, id_libro, id_sede, dias_prestamo, multa_diaria, total_multa)
                    VALUES (:p, :f, :a, :c, :l, :s, :d, :m, :t)"""),
                {
                    "p": int(fila["id_prestamo"]),
                    "f": int(fila["id_fecha"]),
                    "a": int(fila["id_alumno"]),
                    "c": int(fila["id_carrera"]),
                    "l": int(fila["id_libro"]),
                    "s": int(fila["id_sede"]),
                    "d": int(fila["dias_prestamo"]),
                    "m": float(fila["multa_diaria"]),
                    "t": float(fila["total_multa"])
                }
            )
        conn.commit()


def registrar_errores(engine, errores):
    with engine.connect() as conn:
        for e in errores:
            conn.execute(
                text("""INSERT INTO etl_errores
                    (fecha_error, archivo_origen, fila_csv, id_registro, descripcion_error, datos_originales)
                    VALUES (:fecha, :archivo, :fila, :id_reg, :desc, :datos)"""),
                {
                    "fecha": e["fecha_error"],
                    "archivo": e["archivo_origen"],
                    "fila": e["fila_csv"],
                    "id_reg": int(e["id_registro"]) if pd.notna(e["id_registro"]) else None,
                    "desc": e["descripcion_error"],
                    "datos": e["datos_originales"]
                }
            )
        conn.commit()


def registrar_log(engine, resumen):
    with engine.connect() as conn:
        conn.execute(
            text("""INSERT INTO etl_log
                (fecha_ejecucion, archivo_origen, filas_leidas, filas_cargadas, filas_rechazadas, estado)
                VALUES (:fecha, :archivo, :leidas, :cargadas, :rechazadas, :estado)"""),
            {
                "fecha": resumen["fecha_ejecucion"],
                "archivo": resumen["archivo_origen"],
                "leidas": resumen["filas_leidas"],
                "cargadas": resumen["filas_cargadas"],
                "rechazadas": resumen["filas_rechazadas"],
                "estado": resumen["estado"]
            }
        )
        conn.commit()


def generar_reporte(resumen, errores):
    ruta_reporte = os.path.join("evidencias", "reporte_ejecucion.txt")
    os.makedirs("evidencias", exist_ok=True)

    lineas = []
    lineas.append("=" * 55)
    lineas.append("    REPORTE DE EJECUCION - ETL BIBLIOTECA")
    lineas.append("=" * 55)
    lineas.append("")
    lineas.append(f"Nombre del alumno: (pendiente)")
    lineas.append(f"Fecha y hora de ejecucion: {resumen['fecha_ejecucion']}")
    lineas.append(f"Archivo procesado: {resumen['archivo_origen']}")
    lineas.append("")
    lineas.append("-" * 55)
    lineas.append("RESULTADOS")
    lineas.append("-" * 55)
    lineas.append(f"Filas leidas:      {resumen['filas_leidas']}")
    lineas.append(f"Filas cargadas:    {resumen['filas_cargadas']}")
    lineas.append(f"Filas rechazadas:  {resumen['filas_rechazadas']}")
    lineas.append(f"Estado final:      {resumen['estado']}")
    lineas.append("")
    lineas.append("-" * 55)
    lineas.append("ERRORES DETECTADOS")
    lineas.append("-" * 55)
    for e in errores:
        lineas.append(f"  Fila CSV {e['fila_csv']}: {e['descripcion_error']} (id: {e['id_registro']})")
    lineas.append("")
    lineas.append("=" * 55)
    lineas.append("FIN DEL REPORTE")
    lineas.append("=" * 55)

    with open(ruta_reporte, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))

    return ruta_reporte


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

    print("\n" + "=" * 60)
    print("FASE 7 - CARGA DEL DATA WAREHOUSE")
    print("=" * 60)

    cargar_dimensiones(engine, df_validos)
    print(f"[OK] Dimensiones cargadas")

    cargar_hechos(engine, df_validos)
    print(f"[OK] {total_cargadas} registros cargados en fact_prestamos")

    registrar_errores(engine, errores)
    print(f"[OK] {total_rechazadas} errores registrados en etl_errores")

    if total_rechazadas == 0 and total_cargadas > 0:
        estado = "FINALIZADO"
    elif total_rechazadas > 0 and total_cargadas > 0:
        estado = "FINALIZADO_CON_ERRORES"
    else:
        estado = "ERROR_GENERAL"

    resumen = {
        "fecha_ejecucion": datetime.now(),
        "archivo_origen": archivo,
        "filas_leidas": total_leidas,
        "filas_cargadas": total_cargadas,
        "filas_rechazadas": total_rechazadas,
        "estado": estado
    }

    registrar_log(engine, resumen)
    print(f"[OK] Registro guardado en etl_log (Estado: {estado})")

    ruta_reporte = generar_reporte(resumen, errores)
    print(f"[OK] Reporte generado: {ruta_reporte}")

    print("\n" + "=" * 60)
    print("ETL FINALIZADO")
    print("=" * 60)
    print(f"\nResumen:")
    print(f"  Archivo:         {archivo}")
    print(f"  Filas leidas:    {total_leidas}")
    print(f"  Filas cargadas:  {total_cargadas}")
    print(f"  Filas rechazadas:{total_rechazadas}")
    print(f"  Estado:          {estado}")


if __name__ == "__main__":
    main()
