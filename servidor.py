# Archivo: servidor.py
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for
from flask_cors import CORS
import pusher
from decimal import Decimal
from datetime import date, datetime  # datetime importado para filtros
from report_factory import ReportFactory
from db_manager import db_manager

# --- Configuración de la Aplicación ---
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
app.secret_key = 'tu_llave_secreta_aqui_puede_ser_cualquier_texto' #

# --- Configuración de Pusher (Canal actualizado) ---
pusher_client = pusher.Pusher(
    app_id='2073839',
    key='59c8528481ff98495844',
    secret='f1dd25f4e4fa67a5be22',
    cluster='eu',
    ssl=True
)

def notificar_actualizacion_finanzas():
    # NUEVO: Canal renombrado para reflejar todos los datos
    pusher_client.trigger('canal-finanzas', 'evento-actualizacion', {'message': 'actualizar'})

# =========================================================================
# RUTAS PARA SERVIR LAS PÁGINAS HTML (Autenticación)
# =========================================================================

@app.route("/")
def login():
    return render_template("login.html") #

@app.route("/registro")
def registro():
    return render_template("registro.html") #

# --- RUTA PRINCIPAL MODIFICADA ---
@app.route("/dashboard") # ANTES: /calculadora
def dashboard(): # ANTES: calculadora
    if 'idUsuario' not in session:
        return redirect(url_for('login')) #

    con = None
    cursor = None
    try:
        id_usuario_actual = session['idUsuario']

        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor(dictionary=True)
        cursor.execute("SELECT username FROM usuarios WHERE idUsuario = %s", (id_usuario_actual,))
        usuario = cursor.fetchone()
        username = usuario['username'] if usuario else "Usuario"

        # NUEVO: Servimos la nueva plantilla del dashboard
        return render_template("dashboard.html", username=username) 

    except Exception as err:
        print(f"Error en /dashboard: {err}")
        return render_template("dashboard.html", username="Usuario")
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

# =========================================================================
# API DE AUTENTICACIÓN (Sin cambios)
# =========================================================================

@app.route("/registrarUsuario", methods=["POST"])
def registrarUsuario():
    # Esta función se mantiene igual
    con = None
    cursor = None
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor()
        cursor.execute("SELECT idUsuario FROM usuarios WHERE username = %s", (usuario,))
        if cursor.fetchone():
            return make_response(jsonify({"error": "El nombre de usuario ya está en uso."}), 409)

        sql = "INSERT INTO usuarios (username, password) VALUES (%s, %s)"
        cursor.execute(sql, (usuario, password))
        con.commit()
        return make_response(jsonify({"status": "Usuario registrado exitosamente"}), 201)
    
    except Exception as err:
        print(f"Error en /registrarUsuario: {err}")
        if con: con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

@app.route("/iniciarSesion", methods=["POST"])
def iniciarSesion():
    # Esta función se mantiene igual
    con = None
    cursor = None
    try:
        usuario = request.form.get("txtUsuario")
        password = request.form.get("txtContrasena")
        
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor(dictionary=True)
        sql = "SELECT idUsuario, username FROM usuarios WHERE username = %s AND password = %s"
        cursor.execute(sql, (usuario, password))
        user_data = cursor.fetchone()
        
        if user_data:
            session['idUsuario'] = user_data['idUsuario']
            return make_response(jsonify({"status": "success"}), 200)
        else:
            return make_response(jsonify({"error": "Usuario o contraseña incorrectos"}), 401)
    except Exception as err:
        print(f"Error en /iniciarSesion: {err}")
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

@app.route("/cerrarSesion", methods=["POST"])
def cerrarSesion():
    session.clear() #
    return make_response(jsonify({"status": "Sesión cerrada"}), 200)

# =========================================================================
# API PARA FINANZAS (GASTOS) - Rutas actualizadas
# =========================================================================

# --- Función Auxiliar para Obtener Gastos (Modificada) ---
def get_fin_gastos_usuario(id_usuario_actual): # ANTES: get_gastos_usuario
    con = None
    cursor = None
    try:
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor(dictionary=True)
        # NUEVO: Query a fin_gastos y se añade metodo_pago
        sql = """
            SELECT idGasto AS id, descripcion, monto, categoria, fecha, metodo_pago 
            FROM fin_gastos 
            WHERE idUsuario = %s ORDER BY idGasto DESC
        """
        cursor.execute(sql, (id_usuario_actual,))
        gastos_desde_db = cursor.fetchall()
        
        gastos_limpios = []
        for gasto in gastos_desde_db:
            gastos_limpios.append({
                'id': gasto['id'],
                'descripcion': gasto['descripcion'],
                'monto': float(gasto['monto']),
                'categoria': gasto['categoria'],
                'fecha': gasto['fecha'].strftime('%Y-%m-%d'),
                'metodo_pago': gasto['metodo_pago']
            })
        return gastos_limpios
    except Exception as err:
        print(f"Error en get_fin_gastos_usuario: {err}")
        return None
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

# --- Ruta de tabla (Modificada) ---
@app.route("/api/fin/tbodyGastos") # ANTES: /tbodyGastos
def tbodyGastos():
    if 'idUsuario' not in session: return "<tr><td colspan='5'>Acceso no autorizado</td></tr>"

    con = None
    cursor = None
    try:
        id_usuario_actual = session['idUsuario']
        
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor(dictionary=True)
        # NUEVO: Query a fin_gastos y se añade metodo_pago
        sql = """
            SELECT idGasto AS id, descripcion, monto, categoria, fecha, metodo_pago 
            FROM fin_gastos WHERE idUsuario = %s ORDER BY idGasto DESC
        """
        cursor.execute(sql, (id_usuario_actual,))
        gastos_ordenados = cursor.fetchall()
        
        # NUEVO: Apuntamos a un nuevo template (lo crearemos después)
        return render_template("tbodyFinGastos.html", gastos=gastos_ordenados)
    except Exception as err:
        print(f"Error en /api/fin/tbodyGastos: {err}")
        return f"<tr><td colspan='5'>Error al cargar datos: {err}</td></tr>"
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

# --- Ruta JSON (Modificada) ---
@app.route("/api/fin/gastos/json") # ANTES: /gastos/json
def gastos_json():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    id_usuario_actual = session['idUsuario']
    gastos_limpios = get_fin_gastos_usuario(id_usuario_actual) # Función actualizada
    
    if gastos_limpios is None:
         return make_response(jsonify({"error": "Error al obtener gastos de la BD"}), 500)
    
    return jsonify(gastos_limpios)

# --- Ruta Agregar (Modificada) ---
@app.route("/api/fin/gasto", methods=["POST"]) # ANTES: /gasto
def agregar_gasto():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    con = None
    cursor = None
    try:
        id_usuario_actual = session['idUsuario']
        
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor()
        # NUEVO: INSERT en fin_gastos y se añade metodo_pago
        sql = """
            INSERT INTO fin_gastos (descripcion, monto, categoria, fecha, metodo_pago, idUsuario) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        val = (
            request.form.get("descripcion"), float(request.form.get("monto")),
            request.form.get("categoria"), request.form.get("fecha"),
            request.form.get("metodo_pago"), # Nuevo campo
            id_usuario_actual
        )
        cursor.execute(sql, val)
        con.commit()
        notificar_actualizacion_finanzas() # Notificación actualizada
        return make_response(jsonify({"status": "success"}), 201)
    except Exception as err:
        print(f"Error en /api/fin/gasto (agregar): {err}")
        if con: con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

# --- Ruta Eliminar (Modificada) ---
@app.route("/api/fin/gasto/eliminar", methods=["POST"]) # ANTES: /gasto/eliminar
def eliminar_gasto():
    if 'idUsuario' not in session: return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    con = None
    cursor = None
    try:
        id_a_eliminar = int(request.form.get("id"))
        id_usuario_actual = session['idUsuario']
        
        con = db_manager.get_connection()
        if not con: raise Exception("No se pudo conectar a la BD")
            
        cursor = con.cursor()
        # NUEVO: DELETE de fin_gastos
        sql = "DELETE FROM fin_gastos WHERE idGasto = %s AND idUsuario = %s"
        cursor.execute(sql, (id_a_eliminar, id_usuario_actual))
        con.commit()
        notificar_actualizacion_finanzas() # Notificación actualizada
        return make_response(jsonify({"status": "success"}), 200)
    except Exception as err:
        print(f"Error en /api/fin/gasto (eliminar): {err}")
        if con: con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

# =========================================================================
# ¡NUEVO! API PARA FINANZAS (INGRESOS)
# =========================================================================

@app.route("/api/fin/ingresos", methods=["GET"])
def get_ingresos():
    if 'idUsuario' not in session: 
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    con = None
    cursor = None
    try:
        id_usuario_actual = session['idUsuario']
        con = db_manager.get_connection()
        cursor = con.cursor(dictionary=True)
        
        sql = "SELECT idIngreso AS id, descripcion, monto, fuente, fecha FROM fin_ingresos WHERE idUsuario = %s ORDER BY fecha DESC"
        cursor.execute(sql, (id_usuario_actual,))
        ingresos_db = cursor.fetchall()
        
        ingresos_limpios = []
        for ingreso in ingresos_db:
            ingresos_limpios.append({
                'id': ingreso['id'],
                'descripcion': ingreso['descripcion'],
                'monto': float(ingreso['monto']),
                'fuente': ingreso['fuente'],
                'fecha': ingreso['fecha'].strftime('%Y-%m-%d')
            })
        return jsonify(ingresos_limpios)
        
    except Exception as err:
        print(f"Error en /api/fin/ingresos (GET): {err}")
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

@app.route("/api/fin/ingreso", methods=["POST"])
def agregar_ingreso():
    if 'idUsuario' not in session: 
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    con = None
    cursor = None
    try:
        id_usuario_actual = session['idUsuario']
        con = db_manager.get_connection()
        cursor = con.cursor()
        
        sql = "INSERT INTO fin_ingresos (descripcion, monto, fuente, fecha, idUsuario) VALUES (%s, %s, %s, %s, %s)"
        val = (
            request.form.get("descripcion"), float(request.form.get("monto")),
            request.form.get("fuente"), request.form.get("fecha"),
            id_usuario_actual
        )
        cursor.execute(sql, val)
        con.commit()
        notificar_actualizacion_finanzas()
        return make_response(jsonify({"status": "success"}), 201)
        
    except Exception as err:
        print(f"Error en /api/fin/ingreso (POST): {err}")
        if con: con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

# =========================================================================
# ¡NUEVO! API PARA FINANZAS (DEUDAS)
# =========================================================================

@app.route("/api/fin/deudas", methods=["GET"])
def get_deudas():
    if 'idUsuario' not in session: 
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    con = None
    cursor = None
    try:
        id_usuario_actual = session['idUsuario']
        con = db_manager.get_connection()
        cursor = con.cursor(dictionary=True)
        
        sql = "SELECT * FROM fin_deudas WHERE idUsuario = %s ORDER BY estado, fecha_vencimiento"
        cursor.execute(sql, (id_usuario_actual,))
        deudas_db = cursor.fetchall()
        
        deudas_limpias = []
        for deuda in deudas_db:
            deudas_limpias.append({
                'id': deuda['idDeuda'],
                'descripcion': deuda['descripcion'],
                'deudor': deuda['deudor'],
                'monto_total': float(deuda['monto_total']),
                'monto_pagado': float(deuda['monto_pagado']),
                'estado': deuda['estado'],
                'fecha_emision': deuda['fecha_emision'].strftime('%Y-%m-%d'),
                'fecha_vencimiento': deuda['fecha_vencimiento'].strftime('%Y-%m-%d') if deuda['fecha_vencimiento'] else None
            })
        return jsonify(deudas_limpias)
        
    except Exception as err:
        print(f"Error en /api/fin/deudas (GET): {err}")
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

@app.route("/api/fin/deuda", methods=["POST"])
def agregar_deuda():
    if 'idUsuario' not in session: 
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    con = None
    cursor = None
    try:
        id_usuario_actual = session['idUsuario']
        con = db_manager.get_connection()
        cursor = con.cursor()
        
        sql = """
            INSERT INTO fin_deudas (idUsuario, descripcion, deudor, monto_total, monto_pagado, estado, fecha_emision, fecha_vencimiento) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        val = (
            id_usuario_actual,
            request.form.get("descripcion"),
            request.form.get("deudor"),
            float(request.form.get("monto_total")),
            float(request.form.get("monto_pagado", 0)),
            request.form.get("estado", "Pendiente"),
            request.form.get("fecha_emision"),
            request.form.get("fecha_vencimiento") or None
        )
        cursor.execute(sql, val)
        con.commit()
        notificar_actualizacion_finanzas()
        return make_response(jsonify({"status": "success"}), 201)
        
    except Exception as err:
        print(f"Error en /api/fin/deuda (POST): {err}")
        if con: con.rollback()
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

# =========================================================================
# ¡NUEVO! API PARA EL DASHBOARD (Datos Consolidados)
# =========================================================================

@app.route("/api/fin/dashboard_data")
def get_dashboard_data():
    if 'idUsuario' not in session: 
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)
        
    id_usuario_actual = session['idUsuario']
    
    # Obtenemos mes y año de los query params, o usamos el mes/año actual
    try:
        mes = int(request.args.get('mes', datetime.now().month))
        ano = int(request.args.get('ano', datetime.now().year))
    except ValueError:
        mes = datetime.now().month
        ano = datetime.now().year

    con = None
    cursor = None
    try:
        con = db_manager.get_connection()
        cursor = con.cursor(dictionary=True)
        
        # 1. KPIs: Total Ingresado (Mes)
        cursor.execute(
            "SELECT SUM(monto) AS total FROM fin_ingresos WHERE idUsuario = %s AND MONTH(fecha) = %s AND YEAR(fecha) = %s",
            (id_usuario_actual, mes, ano)
        )
        total_ingresado = cursor.fetchone()['total'] or Decimal('0.0')
        
        # 2. KPIs: Total Gastado (Mes)
        cursor.execute(
            "SELECT SUM(monto) AS total FROM fin_gastos WHERE idUsuario = %s AND MONTH(fecha) = %s AND YEAR(fecha) = %s",
            (id_usuario_actual, mes, ano)
        )
        total_gastado = cursor.fetchone()['total'] or Decimal('0.0')
        
        # 3. KPIs: Balance Neto (Mes)
        balance_neto = total_ingresado - total_gastado
        
        # 4. KPIs: Deudas (Total)
        cursor.execute(
            "SELECT COUNT(idDeuda) AS total, SUM(CASE WHEN estado = 'Pendiente' THEN 1 ELSE 0 END) AS pendientes, SUM(CASE WHEN estado = 'Pagada' THEN 1 ELSE 0 END) AS pagadas FROM fin_deudas WHERE idUsuario = %s",
            (id_usuario_actual,)
        )
        deudas_kpi = cursor.fetchone()
        
        # 5. KPIs: Total Saldo Pendiente (Total)
        cursor.execute(
            "SELECT SUM(monto_total - monto_pagado) AS total_pendiente FROM fin_deudas WHERE idUsuario = %s AND estado = 'Pendiente'",
            (id_usuario_actual,)
        )
        total_pendiente = cursor.fetchone()['total_pendiente'] or Decimal('0.0')

        # 6. Gráfico: Gastos por Categoría (Mes)
        cursor.execute(
            "SELECT categoria, SUM(monto) AS total FROM fin_gastos WHERE idUsuario = %s AND MONTH(fecha) = %s AND YEAR(fecha) = %s GROUP BY categoria",
            (id_usuario_actual, mes, ano)
        )
        gastos_categoria = cursor.fetchall()
        
        # 7. Gráfico: Gastos por Método de Pago (Mes)
        cursor.execute(
            "SELECT metodo_pago, SUM(monto) AS total FROM fin_gastos WHERE idUsuario = %s AND MONTH(fecha) = %s AND YEAR(fecha) = %s GROUP BY metodo_pago",
            (id_usuario_actual, mes, ano)
        )
        gastos_metodo_pago = cursor.fetchall()

        # 8. Gráfico: Deudas por Estado (Total)
        cursor.execute(
            "SELECT estado, COUNT(idDeuda) AS total FROM fin_deudas WHERE idUsuario = %s GROUP BY estado",
            (id_usuario_actual,)
        )
        deudas_por_estado = cursor.fetchall()

        # 9. Gráfico: Saldo Pendiente por Deudor (Total)
        cursor.execute(
            "SELECT deudor, SUM(monto_total - monto_pagado) AS pendiente FROM fin_deudas WHERE idUsuario = %s AND estado = 'Pendiente' GROUP BY deudor HAVING pendiente > 0",
            (id_usuario_actual,)
        )
        deudas_por_deudor = cursor.fetchall()

        # Compilamos la respuesta
        dashboard_data = {
            'kpi': {
                'total_ingresado': float(total_ingresado),
                'total_gastado': float(total_gastado),
                'balance_neto': float(balance_neto),
                'deudas_pagadas': deudas_kpi['pagadas'] or 0,
                'deudas_pendientes': deudas_kpi['pendientes'] or 0,
                'total_pendiente': float(total_pendiente)
            },
            'charts': {
                'gastos_categoria': [ {'categoria': g['categoria'], 'total': float(g['total'])} for g in gastos_categoria ],
                'gastos_metodo_pago': [ {'metodo_pago': g['metodo_pago'], 'total': float(g['total'])} for g in gastos_metodo_pago ],
                'deudas_por_estado': [ {'estado': d['estado'], 'total': d['total']} for d in deudas_por_estado ],
                'deudas_por_deudor': [ {'deudor': d['deudor'], 'pendiente': float(d['pendiente'])} for d in deudas_por_deudor ]
            }
        }
        
        return jsonify(dashboard_data)

    except Exception as err:
        print(f"Error en /api/fin/dashboard_data: {err}")
        return make_response(jsonify({"error": f"Error de base de datos: {err}"}), 500)
    finally:
        if cursor: cursor.close()
        if con: db_manager.close_connection(con)

# =========================================================================
# RUTA DE REPORTES (Modificada)
# =========================================================================
@app.route("/api/fin/exportar/<tipo>") # ANTES: /exportar/<tipo>
def exportar_gastos(tipo):
    if 'idUsuario' not in session:
        return make_response(jsonify({"error": "Acceso no autorizado"}), 401)

    try:
        id_usuario_actual = session['idUsuario']
        
        # Usamos la nueva función auxiliar de fin_gastos
        gastos = get_fin_gastos_usuario(id_usuario_actual) 
        
        if gastos is None:
            return make_response(jsonify({"error": "No se pudieron obtener los datos para exportar"}), 500)
        
        factory = ReportFactory()
        
        # (Opcional) Habría que modificar ReportFactory para aceptar los nuevos campos
        # Por ahora, funcionará pero solo exportará los campos que ReporteCSV espere
        
        reporte = factory.crear_reporte(tipo, gastos)
        
        contenido = reporte.generar_reporte()
        
        response = make_response(contenido)
        response.headers['Content-Disposition'] = f'attachment; filename={reporte.get_filename()}'
        response.headers['Content-Type'] = reporte.get_mimetype()
        
        return response

    except ValueError as ve:
        return make_response(jsonify({"error": str(ve)}), 400)
    except Exception as e:
        return make_response(jsonify({"error": f"Error interno del servidor: {e}"}), 500)

# --- FIN DE RUTA ---

if __name__ == "__main__":
    app.run(debug=True, port=5000)
