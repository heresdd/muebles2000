import os
import psycopg2
from psycopg2.extras import RealDictCursor

def connect_to_db():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        return conn
    except psycopg2.Error as err:
        print(f"Error de conexión a la base de datos: {err}")
        raise err