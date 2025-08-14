import mysql.connector

def conectar():
    return mysql.connector.connect(
        host="localhost",
        user="root",           # Cambia si tienes otro usuario
        password="muebles2000",   # Coloca aquí tu contraseña de MySQL
        database="muebles2000"
    )
