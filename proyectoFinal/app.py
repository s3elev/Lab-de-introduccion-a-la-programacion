# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
from iniciar_autofixdb import conectar, crearTablas, guardarClienteWeb, cambiarEstadoServicio, obtenerDashboardData

app = Flask(__name__)
app.secret_key = 'autofix_secure_key_2026'

# Garantizar inicio de las tablas en cada arranque
conn = conectar()
crearTablas(conn)
conn.close()

# --- PANEL PRINCIPAL ---
@app.route('/')
def index():
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM clientes")
    total_c = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM vehiculos")
    total_v = cursor.fetchone()[0] or 0
    
    # Llamamos a la función que acabamos de arreglar arriba
    metricas = obtenerDashboardData(conn)
    
    cursor.execute("""
        SELECT s.id_servicio, c.nombre, v.marca || ' ' || v.modelo, v.placa, s.descripcion_falla, s.costo, s.estado, s.fecha_entrada
        FROM servicios s
        JOIN vehiculos v ON s.id_vehiculo = v.id_vehiculo
        JOIN clientes c ON v.id_cliente = c.id_cliente
        ORDER BY s.id_servicio DESC LIMIT 5
    """)
    recientes = cursor.fetchall()
    conn.close()
    
    # Enviamos los datos desglosados a la plantilla
    return render_template('index.html', 
                           clientes=total_c, 
                           vehiculos=total_v, 
                           pendientes=metricas['pendientes'], 
                           ganancias_hoy=metricas['hoy'],
                           ganancias_mes=metricas['mes'],
                           ganancias_anio=metricas['anio'],
                           servicios=recientes)

# --- CLIENTES (Filtros, Edición, Eliminación) ---
@app.route('/clientes', methods=['GET', 'POST'])
def gestion_clientes():
    conn = conectar()
    cursor = conn.cursor()
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        correo = request.form['correo']
        guardarClienteWeb(conn, nombre, telefono, correo)
        flash('Cliente añadido satisfactoriamente.', 'success')
        return redirect(url_for('gestion_clientes'))
        
    filtro = request.args.get('buscar', '').strip()
    if filtro:
        cursor.execute("SELECT * FROM clientes WHERE nombre LIKE ? OR telefono LIKE ?", (f"%{filtro}%", f"%{filtro}%"))
    else:
        cursor.execute("SELECT * FROM clientes")
    lista = cursor.fetchall()
    conn.close()
    return render_template('clientes.html', clientes=lista, buscar=filtro)

@app.route('/editar_cliente/<int:id>', methods=['POST'])
def editar_cliente(id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE clientes SET nombre=?, telefono=?, correo=? WHERE id_cliente=?", 
                   (request.form['nombre'], request.form['telefono'], request.form['correo'], id))
    conn.commit()
    conn.close()
    flash('Información de cliente guardada.', 'success')
    return redirect(url_for('gestion_clientes'))

@app.route('/eliminar_cliente/<int:id>')
def borrar_cliente(id):
    conn = conectar()
    try:
        conn.cursor().execute("DELETE FROM clientes WHERE id_cliente = ?", (id,))
        conn.commit()
        flash('Cliente borrado de la lista.', 'success')
    except sqlite3.IntegrityError:
        flash('Restricción: El cliente posee autos asociados actualmente en taller.', 'danger')
    conn.close()
    return redirect(url_for('gestion_clientes'))

# --- VEHÍCULOS (Filtros, Edición, Eliminación) ---
@app.route('/vehiculos', methods=['GET', 'POST'])
def gestion_vehiculos():
    conn = conectar()
    cursor = conn.cursor()
    if request.method == 'POST':
        try:
            cursor.execute("INSERT INTO vehiculos (id_cliente, placa, marca, modelo) VALUES (?, ?, ?, ?)",
                           (request.form['id_cliente'], request.form['placa'].upper().strip(), request.form['marca'], request.form['modelo']))
            conn.commit()
            flash('Vehículo dado de alta.', 'success')
        except sqlite3.IntegrityError:
            flash('La matrícula / placa ya se encuentra registrada en el sistema.', 'danger')
        return redirect(url_for('gestion_vehiculos'))
        
    filtro = request.args.get('buscar', '').strip()
    if filtro:
        cursor.execute("""
            SELECT v.id_vehiculo, v.placa, v.marca, v.modelo, c.nombre, v.id_cliente FROM vehiculos v 
            JOIN clientes c ON v.id_cliente = c.id_cliente WHERE v.placa LIKE ? OR c.nombre LIKE ?
        """, (f"%{filtro}%", f"%{filtro}%"))
    else:
        cursor.execute("SELECT v.id_vehiculo, v.placa, v.marca, v.modelo, c.nombre, v.id_cliente FROM vehiculos v JOIN clientes c ON v.id_cliente = c.id_cliente")
    lista_v = cursor.fetchall()
    cursor.execute("SELECT id_cliente, nombre FROM clientes")
    lista_c = cursor.fetchall()
    conn.close()
    return render_template('vehiculos.html', vehiculos=lista_v, clientes=lista_c, buscar=filtro)

@app.route('/editar_vehiculo/<int:id>', methods=['POST'])
def editar_vehiculo(id):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE vehiculos SET placa=?, marca=?, modelo=?, id_cliente=? WHERE id_vehiculo=?",
                       (request.form['placa'].upper().strip(), request.form['marca'], request.form['modelo'], request.form['id_cliente'], id))
        conn.commit()
        flash('Vehículo actualizado correctamente.', 'success')
    except sqlite3.IntegrityError:
        flash('Esa clave de placa ya está asignada a otro vehículo.', 'danger')
    conn.close()
    return redirect(url_for('gestion_vehiculos'))

@app.route('/eliminar_vehiculo/<int:id>')
def borrar_vehiculo(id):
    conn = conectar()
    try:
        conn.cursor().execute("DELETE FROM vehiculos WHERE id_vehiculo = ?", (id,))
        conn.commit()
        flash('Vehículo eliminado del inventario operativo.', 'success')
    except sqlite3.IntegrityError:
        flash('Imposible borrar: El vehículo posee órdenes de servicio vinculadas.', 'danger')
    conn.close()
    return redirect(url_for('gestion_vehiculos'))

# --- SERVICIOS ACTIVOS (Filtros, Edición, Eliminación) ---
@app.route('/servicios', methods=['GET', 'POST'])
def gestion_servicios():
    conn = conectar()
    cursor = conn.cursor()
    estado = request.args.get('estado', '')
    placa = request.args.get('placa', '').upper().strip()
    
    query = """
        SELECT s.id_servicio, c.nombre, v.placa, v.marca || ' ' || v.modelo, s.descripcion_falla, s.diagnostico, s.costo, s.estado, s.fecha_entrada, s.id_vehiculo
        FROM servicios s JOIN vehiculos v ON s.id_vehiculo = v.id_vehiculo JOIN clientes c ON v.id_cliente = c.id_cliente WHERE 1=1
    """
    params = []
    if estado: query += " AND s.estado = ?"; params.append(estado)
    if placa: query += " AND v.placa LIKE ?"; params.append(f"%{placa}%")
    query += " ORDER BY s.id_servicio DESC"
    
    cursor.execute(query, params)
    servicios = cursor.fetchall()
    cursor.execute("SELECT id_vehiculo, placa, marca || ' ' || modelo FROM vehiculos")
    vehiculos = cursor.fetchall()
    conn.close()
    return render_template('servicios.html', servicios=servicios, vehiculos=vehiculos, estado_filtro=estado, buscar_placa=placa)

@app.route('/agregar_servicio', methods=['POST'])
def agregar_servicio():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO servicios (id_vehiculo, descripcion_falla, diagnostico, costo, estado, fecha_entrada) VALUES (?, ?, ?, ?, ?, ?)",
                   (request.form['id_vehiculo'], request.form['falla'], request.form['diagnostico'], float(request.form['costo']), request.form['estado'], datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()
    return redirect(url_for('gestion_servicios'))

@app.route('/editar_servicio/<int:id>', methods=['POST'])
def editar_servicio(id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE servicios SET descripcion_falla=?, diagnostico=?, costo=?, estado=? WHERE id_servicio=?",
                   (request.form['falla'], request.form['diagnostico'], float(request.form['costo']), request.form['estado'], id))
    conn.commit()
    conn.close()
    flash('Órden de trabajo actualizada con éxito.', 'success')
    return redirect(url_for('gestion_servicios'))

@app.route('/eliminar_servicio_web/<int:id>')
def borrar_servicio(id):
    conn = conectar()
    conn.cursor().execute("DELETE FROM servicios WHERE id_servicio = ?", (id,))
    conn.commit()
    conn.close()
    flash('Órden activa eliminada.', 'info')
    return redirect(url_for('gestion_servicios'))

# --- CAJA EN CASCADA INTELIGENTE (Ticket de Pago) ---
@app.route('/liquidar_servicio/<int:id>')
def liquidar_servicio(id):
    conn = conectar()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.id_servicio, c.nombre, c.telefono, v.marca || ' ' || v.modelo, v.placa, s.descripcion_falla, s.diagnostico, s.costo, s.fecha_entrada, c.id_cliente, v.id_vehiculo
        FROM servicios s JOIN vehiculos v ON s.id_vehiculo = v.id_vehiculo JOIN clientes c ON v.id_cliente = c.id_cliente WHERE s.id_servicio = ?
    """, (id,))
    data = cursor.fetchone()
    
    if not data:
        conn.close()
        return redirect(url_for('gestion_servicios'))
        
    id_cliente, id_vehiculo = data[9], data[10]
    fecha_pago = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Mover a la tabla de reportes históricos permanentes
    cursor.execute("""
        INSERT INTO historial_pagos (id_servicio_original, cliente_nombre, cliente_telefono, vehiculo_info, placa, falla, diagnostico, costo, fecha_entrada, fecha_pago)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], fecha_pago))
    
    # Remover el servicio activo de los mecánicos
    cursor.execute("DELETE FROM servicios WHERE id_servicio = ?", (id,))
    
    # Comprobación de borrado inteligente en cascada
    cursor.execute("SELECT COUNT(*) FROM vehiculos WHERE id_cliente = ?", (id_cliente,))
    total_autos = cursor.fetchone()[0]
    
    msg_log = ""
    if total_autos <= 1:
        # Es su único o último coche: Se limpia por completo de la base de datos operativa
        cursor.execute("DELETE FROM vehiculos WHERE id_vehiculo = ?", (id_vehiculo,))
        cursor.execute("DELETE FROM clientes WHERE id_cliente = ?", (id_cliente,))
        msg_log = "Cobro procesado: Se liberó el auto y se dio de baja la cuenta del cliente (Único vehículo registrado)."
    else:
        # Tiene más coches guardados: Solo removemos el auto que sale reparado hoy
        cursor.execute("DELETE FROM vehiculos WHERE id_vehiculo = ?", (id_vehiculo,))
        msg_log = "Cobro procesado: Vehículo retirado de reparaciones (El cliente sigue activo con otros vehículos)."
        
    conn.commit()
    conn.close()
    return render_template('ticket.html', ticket=data, fecha_pago=fecha_pago, nota=msg_log)

# --- PANEL DE HISTORIAL GENERAL DE VENTAS ---
@app.route('/historial')
def ver_historial():
    conn = conectar()
    cursor = conn.cursor()
    
    # Capturar los filtros del formulario web
    cliente = request.args.get('cliente', '').strip()
    placa = request.args.get('placa', '').upper().strip()
    fecha_inicio = request.args.get('fecha_inicio', '').strip()
    fecha_fin = request.args.get('fecha_fin', '').strip()
    
    query = "SELECT * FROM historial_pagos WHERE 1=1"
    params = []
    
    # Filtros de texto existentes
    if cliente: 
        query += " AND cliente_nombre LIKE ?"
        params.append(f"%{cliente}%")
    if placa: 
        query += " AND placa LIKE ?"
        params.append(f"%{placa}%")
        
    # NUEVO: Filtro por rango de fechas (Ignora el filtro si están vacíos)
    if fecha_inicio and fecha_fin:
        query += " AND DATE(fecha_pago) BETWEEN DATE(?) AND DATE(?)"
        params.append(fecha_inicio)
        params.append(fecha_fin)
    
    query += " ORDER BY id_historial DESC"
    
    cursor.execute(query, params)
    registros = cursor.fetchall()
    conn.close()
    
    # Devolvemos los registros y mantenemos los valores en la vista para comodidad del usuario
    return render_template('historial.html', 
                           historial=registros, 
                           buscar_placa=placa, 
                           buscar_cliente=cliente,
                           fecha_inicio=fecha_inicio,
                           fecha_fin=fecha_fin)

@app.route('/eliminar_historial/<int:id>')
def eliminar_historial(id):
    conn = conectar()
    conn.cursor().execute("DELETE FROM historial_pagos WHERE id_historial = ?", (id,))
    conn.commit()
    conn.close()
    flash('Registro financiero removido de la auditoría.', 'info')
    return redirect(url_for('ver_historial'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)