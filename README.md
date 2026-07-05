# Unidad 2 - ETL Biblioteca

Proyecto de ETL utilizando Python, Pandas y MySQL.

## Objetivo

Desarrollar un proceso ETL (Extract, Transform, Load) que lee un archivo CSV con datos de prestamos de biblioteca, aplica limpieza y validaciones, y carga los datos en un mini Data Warehouse en MySQL para su analisis posterior.

## Requisitos

- Python 3.13+
- MySQL 8.4 instalado y corriendo en `localhost:3306`
- Git (para el control de versiones)

## Estructura del proyecto

```
unidad2_etl_biblioteca/
├── data/
│   └── prestamos_biblioteca_100.csv
├── scripts/
│   └── etl_biblioteca.py
├── sql/
│   └── consultas_verificacion.sql
├── evidencias/
│   ├── evidencias_unidad2.pdf
│   └── reporte_ejecucion.txt
├── .venv/
├── .gitignore
├── README.md
└── requirements.txt
```

## Crear la base de datos

La base de datos se crea automaticamente al ejecutar el script. Tambien puedes crearla manualmente:

```sql
CREATE DATABASE IF NOT EXISTS biblioteca_dw;
```

## Instalacion

1. Crear el entorno virtual:

```powershell
python -m venv .venv
```

2. Activar el entorno virtual:

```powershell
.venv\Scripts\Activate.ps1
```

3. Instalar dependencias:

```powershell
pip install pandas sqlalchemy pymysql openpyxl
```

O bien:

```powershell
pip install -r requirements.txt
```

## Ejecucion

Asegurate de que MySQL este corriendo y ejecuta:

```powershell
python scripts/etl_biblioteca.py
```

El script:
1. Lee el CSV desde `data/prestamos_biblioteca_100.csv`
2. Limpia y estandariza los datos
3. Se conecta a MySQL y crea las tablas del Data Warehouse
4. Valida los registros (total_multa correcto y sin duplicados)
5. Carga los datos validos en las dimensiones y tabla de hechos
6. Registra los errores en `etl_errores`
7. Guarda la bitacora en `etl_log`
8. Genera el reporte en `evidencias/reporte_ejecucion.txt`

## Resultado esperado

```
Filas leidas: 100
Filas cargadas: 98
Filas rechazadas: 2
Estado: FINALIZADO_CON_ERRORES

Errores:
- Fila 100: total_multa incorrecto (id: 5099)
- Fila 101: id_prestamo duplicado (id: 5002)
```

## Tablas del Data Warehouse

- `dim_alumno` - Dimension de alumnos
- `dim_carrera` - Dimension de carreras
- `dim_libro` - Dimension de libros
- `dim_sede` - Dimension de sedes
- `dim_fecha` - Dimension de fechas
- `fact_prestamos` - Tabla de hechos de prestamos
- `etl_errores` - Registro de errores del ETL
- `etl_log` - Bitacora de ejecuciones
