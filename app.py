from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from conexion import conectar
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import pandas as pd
from fpdf import FPDF
from datetime import datetime

app = Flask(__name__)
# ¡IMPORTANTE! Cambia esta clave secreta por una cadena larga y aleatoria.
app.secret_key = 'b8a9d8c7c6e5a4b3f2e1d0c9b8a7f6e5d4c3b2a1e0d9c8b7'

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            flash("Necesitas iniciar sesión para acceder a esta página.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para proteger rutas por rol
def rol_required(rol_permitido):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'rol' in session and (session['rol'] == rol_permitido or session['rol'] == 'gerente'):
                return f(*args, **kwargs)
            flash("No tienes permisos para acceder a esta página.", "danger")
            return redirect(url_for('index'))
        return decorated_function
    return decorator

@app.route('/')
def index():
    return render_template('index.html')

# --- RUTAS DE INVENTARIO ---

@app.route('/inventario')
@login_required
def inventario():
    productos = []
    query = request.args.get('query', '')
    
    try:
        db = conectar()
        cursor = db.cursor(dictionary=True)
        sql_query = "SELECT * FROM productos"
        params = []
        
        if query:
            sql_query += " WHERE nombre LIKE %s OR categoria LIKE %s OR color LIKE %s"
            search_param = f"%{query}%"
            params.extend([search_param, search_param, search_param])
        
        sql_query += " ORDER BY categoria, nombre"
        
        cursor.execute(sql_query, params)
        productos = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Error de base de datos: {err}", "danger")
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
            
    return render_template('inventario.html', productos=productos, query=query)

@app.route('/inventario/nuevo', methods=['POST'])
@login_required
@rol_required('gerente')
def nuevo_producto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        color = request.form['color']
        precio = request.form['precio']
        cantidad = request.form['cantidad']
        descripcion = request.form['descripcion']

        try:
            db = conectar()
            cursor = db.cursor()
            cursor.execute("INSERT INTO productos (nombre, categoria, color, precio, cantidad, descripcion) VALUES (%s, %s, %s, %s, %s, %s)",
                           (nombre, categoria, color, precio, cantidad, descripcion))
            db.commit()
            flash("Producto registrado exitosamente.", "success")
        except mysql.connector.Error as err:
            flash(f"Error al registrar el producto: {err}", "danger")
        finally:
            if 'db' in locals() and db.is_connected():
                cursor.close()
                db.close()
    return redirect(url_for('inventario'))

@app.route('/inventario/editar', methods=['POST'])
@login_required
@rol_required('gerente')
def editar_producto():
    if request.method == 'POST':
        producto_id = request.form['id']
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        color = request.form['color']
        precio = request.form['precio']
        cantidad = request.form['cantidad']
        descripcion = request.form['descripcion']
        
        try:
            db = conectar()
            cursor = db.cursor()
            cursor.execute("UPDATE productos SET nombre = %s, categoria = %s, color = %s, precio = %s, cantidad = %s, descripcion = %s WHERE id = %s",
                           (nombre, categoria, color, precio, cantidad, descripcion, producto_id))
            db.commit()
            flash("Producto actualizado exitosamente.", "success")
        except mysql.connector.Error as err:
            flash(f"Error al actualizar el producto: {err}", "danger")
        finally:
            if 'db' in locals() and db.is_connected():
                cursor.close()
                db.close()
    return redirect(url_for('inventario'))

@app.route('/inventario/eliminar/<int:producto_id>', methods=['POST'])
@login_required
@rol_required('gerente')
def eliminar_producto(producto_id):
    try:
        db = conectar()
        cursor = db.cursor()
        cursor.execute("DELETE FROM productos WHERE id = %s", (producto_id,))
        db.commit()
        flash("Producto eliminado exitosamente.", "success")
    except mysql.connector.Error as err:
        flash(f"Error al eliminar el producto: {err}", "danger")
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
    return redirect(url_for('inventario'))

# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    hay_usuarios = False
    try:
        db = conectar()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        count = cursor.fetchone()[0]
        if count > 0:
            hay_usuarios = True
    except mysql.connector.Error as err:
        flash(f"Error al conectar con la base de datos: {err}", "danger")
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
            return redirect(url_for('index'))
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()

    if hay_usuarios and (not session.get('loggedin') or session.get('rol') != 'gerente'):
        flash("No tienes permisos para registrar nuevos usuarios.", "danger")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        rol = request.form.get('rol', 'trabajador')
        
        if not hay_usuarios:
            rol = 'gerente'
            
        hashed_password = generate_password_hash(password)
        
        try:
            db = conectar()
            cursor = db.cursor()
            cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES (%s, %s, %s)", (username, hashed_password, rol))
            db.commit()
            flash(f"Usuario {username} registrado exitosamente como {rol}.", "success")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Error al registrar el usuario: {err}", "danger")
        finally:
            if 'db' in locals() and db.is_connected():
                cursor.close()
                db.close()
    
    return render_template('registro.html', hay_usuarios=hay_usuarios)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            db = conectar()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['loggedin'] = True
                session['id'] = user['id']
                session['username'] = user['username']
                session['rol'] = user['rol']
                flash(f"¡Bienvenido, {user['username']}! Has iniciado sesión como {user['rol']}.", "success")
                return redirect(url_for('inventario'))
            else:
                flash("Nombre de usuario o contraseña incorrectos.", "danger")
        except mysql.connector.Error as err:
            flash(f"Error al conectar con la base de datos: {err}", "danger")
        finally:
            if 'db' in locals() and db.is_connected():
                cursor.close()
                db.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('rol', None)
    flash("Has cerrado sesión exitosamente.", "info")
    return redirect(url_for('index'))

@app.route('/ventas/nueva', methods=['GET', 'POST'])
@login_required
@rol_required('trabajador')
def nueva_venta():
    if request.method == 'POST':
        cliente_cedula = request.form['cliente_cedula']
        total_venta = request.form['total_venta']
        metodo_pago = request.form['metodo_pago']
        descripcion = request.form['descripcion_general']
        productos_json = request.form['productos_vendidos']
        
        import json
        productos_vendidos = json.loads(productos_json)
        
        try:
            db = conectar()
            cursor = db.cursor()
            db.autocommit = False 
            
            cursor.execute("SELECT id FROM clientes WHERE cedula = %s", (cliente_cedula,))
            cliente_id = cursor.fetchone()
            
            if not cliente_id:
                flash(f"Cliente con cédula {cliente_cedula} no encontrado. Por favor, regístrelo primero.", "danger")
                db.rollback()
                return redirect(url_for('nueva_venta'))
            
            cliente_id = cliente_id[0]
            
            cursor.execute("INSERT INTO ventas (id_cliente, fecha, total, metodo_pago, descripcion) VALUES (%s, NOW(), %s, %s, %s)",
                           (cliente_id, total_venta, metodo_pago, descripcion))
            venta_id = cursor.lastrowid
            
            for producto in productos_vendidos:
                id_producto = producto['id']
                cantidad_vendida = producto['cantidad']
                
                cursor.execute("SELECT cantidad FROM productos WHERE id = %s", (id_producto,))
                stock_actual = cursor.fetchone()[0]
                
                if stock_actual < cantidad_vendida:
                    flash(f"No hay suficiente stock para el producto ID {id_producto}. Stock disponible: {stock_actual}", "danger")
                    db.rollback()
                    return redirect(url_for('nueva_venta'))
                
                cursor.execute("INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario, descripcion) VALUES (%s, %s, %s, (SELECT precio FROM productos WHERE id = %s), %s)",
                               (venta_id, id_producto, cantidad_vendida, id_producto, producto['descripcion_producto']))

                cursor.execute("UPDATE productos SET cantidad = cantidad - %s WHERE id = %s", (cantidad_vendida, id_producto))
            
            db.commit()
            flash(f"Venta ID {venta_id} registrada exitosamente.", "success")
            return redirect(url_for('inventario'))
            
        except mysql.connector.Error as err:
            flash(f"Error en la transacción: {err}", "danger")
            db.rollback()
            return redirect(url_for('nueva_venta'))
        finally:
            if 'db' in locals() and db.is_connected():
                cursor.close()
                db.close()
    
    clientes = []
    productos = []
    try:
        db = conectar()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre, cedula FROM clientes")
        clientes = cursor.fetchall()
        cursor.execute("SELECT id, nombre, precio, cantidad FROM productos")
        productos = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Error de base de datos: {err}")
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
            
    return render_template('nueva_venta.html', clientes=clientes, productos=productos)

@app.route('/historial/ventas')
@login_required
def historial_ventas():
    ventas = []
    query = request.args.get('query', '')
    fecha_inicio = request.args.get('fecha_inicio', '')
    fecha_fin = request.args.get('fecha_fin', '')

    try:
        db = conectar()
        cursor = db.cursor(dictionary=True)

        sql_query = """
            SELECT
                v.id,
                v.fecha,
                c.nombre AS nombre_cliente,
                c.cedula AS cedula_cliente,
                v.total,
                v.metodo_pago,
                v.descripcion
            FROM ventas v
            JOIN clientes c ON v.id_cliente = c.id
        """
        
        conditions = []
        params = []
        
        if query:
            conditions.append("(c.nombre LIKE %s OR c.cedula LIKE %s)")
            params.extend([f"%{query}%", f"%{query}%"])

        if fecha_inicio:
            conditions.append("v.fecha >= %s")
            params.append(fecha_inicio)
            
        if fecha_fin:
            conditions.append("v.fecha <= %s")
            params.append(fecha_fin)
            
        if conditions:
            sql_query += " WHERE " + " AND ".join(conditions)
        
        sql_query += " ORDER BY v.fecha DESC"
        
        cursor.execute(sql_query, params)
        ventas = cursor.fetchall()
        
        # Para cada venta, obtenemos los productos vendidos
        for venta in ventas:
            cursor.execute("""
                SELECT
                    p.nombre AS nombre_producto,
                    dv.cantidad,
                    dv.precio_unitario,
                    dv.descripcion
                FROM detalle_ventas dv
                JOIN productos p ON dv.id_producto = p.id
                WHERE dv.id_venta = %s
            """, (venta['id'],))
            venta['detalle'] = cursor.fetchall()
            
    except mysql.connector.Error as err:
        flash(f"Error al cargar el historial de ventas: {err}", "danger")
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
            
    return render_template('historial_ventas.html', ventas=ventas, query=query, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

@app.route('/reportes/ventas', methods=['GET'])
@login_required
@rol_required('gerente')
def reportes_ventas():
    return render_template('reportes_ventas.html')

@app.route('/reportes/generar', methods=['POST'])
@login_required
@rol_required('gerente')
def generar_reporte_ventas():
    report_type = request.form.get('report_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    ventas = []
    try:
        db = conectar()
        cursor = db.cursor(dictionary=True)
        sql_query = """
            SELECT
                v.id,
                v.fecha,
                c.nombre AS nombre_cliente,
                c.cedula AS cedula_cliente,
                v.total,
                v.metodo_pago,
                v.descripcion
            FROM ventas v
            JOIN clientes c ON v.id_cliente = c.id
            WHERE v.fecha BETWEEN %s AND %s
            ORDER BY v.fecha DESC
        """
        cursor.execute(sql_query, (start_date, end_date))
        ventas = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Error al generar el reporte: {err}", "danger")
        return redirect(url_for('reportes_ventas'))
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
            
    if not ventas:
        flash("No se encontraron ventas para el rango de fechas seleccionado.", "info")
        return redirect(url_for('reportes_ventas'))

    df = pd.DataFrame(ventas)
    
    if report_type == 'excel':
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Reporte de Ventas', index=False)
        output.seek(0)
        return Response(output.read(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f"attachment;filename=reporte_ventas_{start_date}_a_{end_date}.xlsx"})
        
    elif report_type == 'pdf':
        class PDF(FPDF):
            def header(self):
                self.set_font('Arial', 'B', 12)
                self.cell(0, 10, 'Reporte de Ventas', 0, 1, 'C')
                self.ln(10)

            def footer(self):
                self.set_y(-15)
                self.set_font('Arial', 'I', 8)
                self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

            def chapter_title(self, title):
                self.set_font('Arial', 'B', 12)
                self.cell(0, 10, title, 0, 1, 'L')
                self.ln(5)

            def chapter_body(self, data):
                self.set_font('Arial', '', 10)
                for index, row in data.iterrows():
                    self.cell(0, 6, f"ID de Venta: {row['id']}", 0, 1)
                    self.cell(0, 6, f"Fecha: {row['fecha']}", 0, 1)
                    self.cell(0, 6, f"Cliente: {row['nombre_cliente']} ({row['cedula_cliente']})", 0, 1)
                    self.cell(0, 6, f"Total: ${row['total']}", 0, 1)
                    self.cell(0, 6, f"Método de Pago: {row['metodo_pago']}", 0, 1)
                    self.cell(0, 6, f"Descripción: {row['descripcion']}", 0, 1)
                    self.ln(5)

        pdf = PDF()
        pdf.add_page()
        pdf.chapter_body(df)
        
        response = Response(pdf.output(dest='S'), mimetype='application/pdf')
        response.headers['Content-Disposition'] = f'attachment;filename=reporte_ventas_{start_date}_a_{end_date}.pdf'
        return response

    return redirect(url_for('reportes_ventas'))

# --- RUTAS DE GESTIÓN DE CLIENTES ---

@app.route('/clientes')
@login_required
@rol_required('gerente')
def clientes():
    clientes_list = []
    query = request.args.get('query', '')
    try:
        db = conectar()
        cursor = db.cursor(dictionary=True)
        
        sql_query = "SELECT * FROM clientes"
        params = []
        
        if query:
            sql_query += " WHERE nombre LIKE %s OR cedula LIKE %s OR telefono LIKE %s OR direccion LIKE %s"
            search_param = f"%{query}%"
            params.extend([search_param, search_param, search_param, search_param])
        
        sql_query += " ORDER BY nombre"
        
        cursor.execute(sql_query, params)
        clientes_list = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f"Error al cargar la lista de clientes: {err}", "danger")
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
    return render_template('clientes.html', clientes=clientes_list, query=query)

@app.route('/clientes/nuevo', methods=['POST'])
@login_required
@rol_required('gerente')
def nuevo_cliente():
    if request.method == 'POST':
        nombre = request.form['nombre']
        cedula = request.form['cedula']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        
        try:
            db = conectar()
            cursor = db.cursor()
            cursor.execute("INSERT INTO clientes (nombre, cedula, telefono, direccion) VALUES (%s, %s, %s, %s)",
                           (nombre, cedula, telefono, direccion))
            db.commit()
            flash("Cliente registrado exitosamente.", "success")
        except mysql.connector.Error as err:
            flash(f"Error al registrar el cliente: {err}", "danger")
        finally:
            if 'db' in locals() and db.is_connected():
                cursor.close()
                db.close()

        redirect_to = request.form.get('redirect_to')
        if redirect_to:
            return redirect(redirect_to)

    return redirect(url_for('clientes'))

@app.route('/clientes/editar', methods=['POST'])
@login_required
@rol_required('gerente')
def editar_cliente():
    if request.method == 'POST':
        cliente_id = request.form['id']
        nombre = request.form['nombre']
        cedula = request.form['cedula']
        telefono = request.form['telefono']
        direccion = request.form['direccion']
        try:
            db = conectar()
            cursor = db.cursor()
            cursor.execute("UPDATE clientes SET nombre = %s, cedula = %s, telefono = %s, direccion = %s WHERE id = %s",
                           (nombre, cedula, telefono, direccion, cliente_id))
            db.commit()
            flash("Cliente actualizado exitosamente.", "success")
        except mysql.connector.Error as err:
            flash(f"Error al actualizar el cliente: {err}", "danger")
        finally:
            if 'db' in locals() and db.is_connected():
                cursor.close()
                db.close()
    return redirect(url_for('clientes'))

@app.route('/clientes/eliminar/<int:cliente_id>', methods=['POST'])
@login_required
@rol_required('gerente')
def eliminar_cliente(cliente_id):
    try:
        db = conectar()
        cursor = db.cursor()
        cursor.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        db.commit()
        flash("Cliente eliminado exitosamente.", "success")
    except mysql.connector.Error as err:
        flash(f"Error al eliminar el cliente: {err}", "danger")
    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
    return redirect(url_for('clientes'))

if __name__ == '__main__':
    app.run(debug=True)