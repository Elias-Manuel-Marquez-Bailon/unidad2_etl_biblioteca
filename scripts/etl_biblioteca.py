import pandas as pd
from sqlalchemy import create_engine, text
import os
from datetime import datetime


def conectar_db():
    pass


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


def validar_datos(df):
    pass


def crear_tablas(engine):
    pass


def limpiar_tablas(engine):
    pass


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


if __name__ == "__main__":
    main()
