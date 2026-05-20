# -------------------------------------------------
# AUTOFIX - SISTEMA DE TALLER MECÁNICO
# DESARROLLADO POR:
# 1.- JUAN LUIS AGUILAR MONTAÑEZ
# 2.- HUGO EDUARDO ZENDEJAS GONZÁLEZ
# -------------------------------------------------

# Importar librerías necesarias
import sqlite3
from datetime import datetime

# Nombre de la base de datos
db_nombre = "autofix.db"


# FUNCIÓN PARA CONECTAR A LA BASE DE DATOS
def conectar():
    #Crea y retorna una conexión a la base de datos.
    #También activa las llaves foráneas.

    conexion = sqlite3.connect(db_nombre)

    # Activar relaciones entre tablas
    conexion.execute("PRAGMA foreign_keys = ON")

    return conexion


# CREACIÓN DE TABLAS
def crearTablas(conexion):
    #Crea las tablas del sistema si no existen.

    cursor = conexion.cursor()


    # Tabla CLIENTES
    # Guarda información de los dueños de los vehiculos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT NOT NULL,
        correo TEXT DEFAULT 'No proporcionado'
    )
    """)


    # Tabla VEHICULOS
    # Guarda vehículos de cada cliente
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehiculos (
        id_vehiculo INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cliente INTEGER,
        placa TEXT NOT NULL UNIQUE,
        marca TEXT NOT NULL,
        modelo TEXT NOT NULL,

        FOREIGN KEY(id_cliente) 
        REFERENCES clientes(id_cliente)
    )
    """)


    # Tabla SERVICIOS
    # Guarda servicios realizados a cada vehiculo
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicios (
        id_servicio INTEGER PRIMARY KEY AUTOINCREMENT,
        id_vehiculo INTEGER,
        descripcion_falla TEXT NOT NULL,
        diagnostico TEXT NOT NULL,
        costo REAL NOT NULL,
        estado TEXT NOT NULL,
        fecha_entrada TEXT NOT NULL,

        FOREIGN KEY(id_vehiculo) 
        REFERENCES vehiculos(id_vehiculo)
    )
    """)

    # TABLA AGREGADA: HISTORIAL DE PAGOS
    # Almacena el histórico permanente de servicios cobrados para no perder auditoría
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_pagos (
        id_historial INTEGER PRIMARY KEY AUTOINCREMENT,
        id_servicio_original INTEGER,
        cliente_nombre TEXT,
        cliente_telefono TEXT,
        vehiculo_info TEXT,
        placa TEXT,
        falla TEXT,
        diagnostico TEXT,
        costo REAL,
        fecha_entrada TEXT,
        fecha_pago TEXT
    )
    """)

    # Guardar cambios
    conexion.commit()


# INSERTAR CLIENTE
def datosCliente(conexion):
    #Guarda un cliente en la base de datos.

    try:
        nombre = input("NOMBRE: ")
        telefono = input("TELEFONO: ")
        correo = input("CORREO: ")

        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO clientes 
            (
                nombre, 
                telefono, 
                correo
            ) 
            VALUES (?, ?, ?) 
        """, (
            nombre, 
            telefono, 
            correo
        ))

        conexion.commit()

        print("Cliente guardado correctamente.")

    except Exception as e:
        print(f"Error al guardar cliente: {e}")


# INSERTAR VEHÍCULO
def datosVehiculo(conexion):
    #Guarda un vehículo relacionado a un cliente.

    try:
        placa = input("PLACA: ")
        marca = input("MARCA: ")
        modelo = input("MODELO: ")

        id_cliente = input("ID DEL CLIENTE: ")

        # Verificar que sea numérico
        if not id_cliente.isdigit():
            print("El ID debe ser numérico.")
            return

        id_cliente = int(id_cliente)

        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO vehiculos 
            (
                placa, 
                marca, 
                modelo, 
                id_cliente
            ) 
            VALUES (?, ?, ?, ?) 
        """, (
            placa, 
            marca, 
            modelo, 
            id_cliente
        ))

        conexion.commit()

        print("Vehículo guardado correctamente.")

    except Exception as e:
        print(f"Error al guardar vehículo: {e}")


# INSERTAR SERVICIO
def datosServicio(conexion):
    #Guarda un servicio realizado a un vehículo.

    try:
        id_vehiculo = input("ID DEL VEHICULO: ")

        # Verificar que sea numérico
        if not id_vehiculo.isdigit():
            print("El ID debe ser numérico.")
            return

        id_vehiculo = int(id_vehiculo)

        descripcionFalla = input("FALLA: ")
        diagnostico = input("DIAGNOSTICO: ")

        while True:
            try:
                costo = float(input("COSTO: "))
                break

            except ValueError:
                print("Error: el costo debe ser un valor númerico.")

        estado = input("ESTADO: ")

        # Fecha automática
        fechaEntrada = datetime.now().strftime("%Y-%m-%d")

        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO servicios
            (
                id_vehiculo,
                descripcion_falla,
                diagnostico,
                costo,
                estado,
                fecha_entrada
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            id_vehiculo,
            descripcionFalla,
            diagnostico,
            costo,
            estado,
            fechaEntrada
        ))

        conexion.commit()

        print("Servicio guardado correctamente.")

    except Exception as e:
        print("Error al guardar servicio:", e)


# MOSTRAR TABLAS
def verTabla(conexion, tabla):
    #Muestra todos los registros de una tabla.

    cursor = conexion.cursor()

    cursor.execute(f"SELECT * FROM {tabla}")

    filas = cursor.fetchall()

    for fila in filas:
        print(fila)


# BUSCADOR GENERAL
def buscar(conexion, tabla, campo, valor):
    #Busca registros usando LIKE.

    cursor = conexion.cursor()

    cursor.execute(f"""
        SELECT * FROM {tabla}
        WHERE {campo} LIKE ?
    """, (f"%{valor}%",))

    return cursor.fetchall()


# REPORTE COMPLETO
def reporteCompleto(conexion):
    #Muestra cliente, vehículo y estado del servicio.

    cursor = conexion.cursor()

    cursor.execute("""
        SELECT
            clientes.nombre,
            vehiculos.placa,
            servicios.estado

        FROM clientes

        JOIN vehiculos
        ON clientes.id_cliente = vehiculos.id_cliente

        JOIN servicios
        ON vehiculos.id_vehiculo = servicios.id_vehiculo
    """)

    return cursor.fetchall()


# CAMBIAR ESTADO DE SERVICIO
def cambiarEstadoServicio(conexion, id_servicio, nuevo_estado):
    #Cambia el estado de un servicio.

    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE servicios
        SET estado = ?
        WHERE id_servicio = ?
    """, (nuevo_estado, id_servicio))

    conexion.commit()


# FILTRO DE SERVICIOS PENDIENTES
def serviciosPendientes(conexion):
    #Muestra servicios pendientes.

    cursor = conexion.cursor()

    cursor.execute("""
        SELECT * FROM servicios
        WHERE estado = 'Pendiente'
    """)

    return cursor.fetchall()


# ACTUALIZAR DATOS
def actualizar(
    conexion,
    tabla,
    id_campo,
    id_valor,
    campo,
    nuevo_valor
):
    #Actualiza un dato específico.

    cursor = conexion.cursor()

    cursor.execute(f"""
        UPDATE {tabla}
        SET {campo} = ?
        WHERE {id_campo} = ?
    """, (nuevo_valor, id_valor))

    conexion.commit()


# ELIMINAR SERVICIO
def eliminarServicio(conexion):
    #Elimina un servicio usanod su ID
    id_servicio = input("ID DEL SERVICIO: ")

    # Verificar número
    if not id_servicio.isdigit():
        print("El ID debe ser numérico.")
        return

    id_servicio = int(id_servicio)

    cursor = conexion.cursor()

    cursor.execute("""
        DELETE FROM servicios
        WHERE id_servicio = ?
    """, (id_servicio,))

    conexion.commit()

    print("Servicio eliminado correctamente.")


# ELIMINAR CLIENTE
def eliminarCliente(conexion, id_cliente):

    cursor = conexion.cursor()

    cursor.execute("""
        DELETE FROM clientes
        WHERE id_cliente = ?
    """, (id_cliente,))

    conexion.commit()


# ELIMINAR VEHICULO
def eliminarVehiculo(conexion, id_vehiculo):

    cursor = conexion.cursor()

    cursor.execute("""
        DELETE FROM vehiculos
        WHERE id_vehiculo = ?
    """, (id_vehiculo,))

    conexion.commit()


# TICKET DEL SERVICIO
def generarTicket(conexion, id_servicio):

    cursor = conexion.cursor()

    cursor.execute("""
    SELECT
        clientes.nombre,
        vehiculos.placa,
        vehiculos.marca,
        vehiculos.modelo,
        servicios.descripcion_falla,
        servicios.diagnostico,
        servicios.costo,
        servicios.estado,
        servicios.fecha_entrada

    FROM servicios

    JOIN vehiculos
    ON servicios.id_vehiculo = vehiculos.id_vehiculo

    JOIN clientes
    ON vehiculos.id_cliente = clientes.id_cliente

    WHERE servicios.id_servicio = ?
    """, (id_servicio,))

    ticket = cursor.fetchone()

    if ticket:

        print("\n========== TICKET ==========")

        print("CLIENTE:", ticket[0])
        print("PLACA:", ticket[1])
        print("MARCA:", ticket[2])
        print("MODELO:", ticket[3])
        print("FALLA:", ticket[4])
        print("DIAGNÓSTICO:", ticket[5])
        print("COSTO:", ticket[6])
        print("ESTADO:", ticket[7])
        print("FECHA:", ticket[8])

        print("============================")

    else:
        print("Servicio no encontrado.")


# GANANCIAS DIARIAS
def gananciasHoy(conexion):

    fecha = datetime.now().strftime("%Y-%m-%d")

    cursor = conexion.cursor()

    cursor.execute("""
    SELECT SUM(costo)
    FROM servicios
    WHERE fecha_entrada = ?
    """, (fecha,))

    total = cursor.fetchone()[0]

    if total is None:
        total = 0

    print(f"Ganancias de hoy: ${total}")


# LISTA DE SERVICIOS
def listaServicios(conexion):

    cursor = conexion.cursor()

    cursor.execute("""
    SELECT id_servicio, estado
    FROM servicios
    """)

    servicios = cursor.fetchall()

    lista = []

    for servicio in servicios:
        lista.append(servicio)

    return lista


def obtenerDashboardData(conexion):
    # Obtiene estadísticas rápidas calculando el dinero real del historial
    cursor = conexion.cursor()
    hoy = datetime.now().strftime("%Y-%m-%d")
    mes = datetime.now().strftime("%Y-%m")
    anio = datetime.now().strftime("%Y")
    
    # Ganancias del Día (Miras lo cobrado hoy)
    cursor.execute("SELECT SUM(costo) FROM historial_pagos WHERE fecha_pago LIKE ?", (f"{hoy}%",))
    ganancias_hoy = cursor.fetchone()[0] or 0
    
    # Ganancias del Mes
    cursor.execute("SELECT SUM(costo) FROM historial_pagos WHERE fecha_pago LIKE ?", (f"{mes}%",))
    ganancias_mes = cursor.fetchone()[0] or 0
    
    # Ganancias del Año
    cursor.execute("SELECT SUM(costo) FROM historial_pagos WHERE fecha_pago LIKE ?", (f"{anio}%",))
    ganancias_anio = cursor.fetchone()[0] or 0
    
    # Cantidad de servicios pendientes en el taller
    cursor.execute("SELECT COUNT(*) FROM servicios WHERE estado = 'Pendiente'")
    pendientes = cursor.fetchone()[0] or 0
        
    return {
        "hoy": ganancias_hoy, 
        "mes": ganancias_mes, 
        "anio": ganancias_anio, 
        "pendientes": pendientes
    }


def guardarClienteWeb(conexion, nombre, telefono, correo):
    # Guarda un cliente desde el formulario de la interfaz web
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO clientes 
            (
                nombre, 
                telefono, 
                correo
            ) 
            VALUES (?, ?, ?) 
        """, (
            nombre, 
            telefono, 
            correo if correo else 'No proporcionado'
        ))
        conexion.commit()
        return True
    except Exception as e:
        print(f"Error al guardar cliente desde web: {e}")
        return False

# EJECUCIÓN PRINCIPAL
if __name__ == "__main__":

    # Crear conexión
    conexion = conectar()

    # Crear tablas
    crearTablas(conexion)

    print("Base de datos AutoFix lista correctamente.")