import os
import psycopg2
import urllib.parse

def conectar():
    # Obtén la URL de la base de datos de las variables de entorno
    url = os.environ.get('DATABASE_URL')
    if url is None:
        # Aquí puedes poner tus credenciales locales para desarrollo
        raise ValueError("DATABASE_URL no está configurada")

    # Conéctate usando la URL
    return psycopg2.connect(url)
