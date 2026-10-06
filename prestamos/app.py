import os
import logging
from datetime import datetime, timedelta
import requests
from flask import Flask, request, jsonify
from database import init_db, get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prestamos")

app = Flask(__name__)

# Configuration from Environment Variables
CATALOGO_URL = os.getenv("CATALOGO_URL", "http://catalogo:8001")
NOTIFICACIONES_URL = os.getenv("NOTIFICACIONES_URL", "http://notificaciones:8003")
DIAS_PRESTAMO = int(os.getenv("DIAS_PRESTAMO", 7))
MULTA_POR_DIA = float(os.getenv("MULTA_POR_DIA", 5))
DIAS_AVISO = int(os.getenv("DIAS_AVISO", 2))

with app.app_context():
    init_db()

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return datetime.strptime(date_str, "%Y-%m-%d")

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "UP"}), 200

# --- PRESTAMOS ENDPOINTS ---

@app.route('/prestamos', methods=['POST'])
def crear_prestamo():
    data = request.get_json() or {}
    usuario = data.get('usuario')
    libro_id = data.get('libro_id')

    if not usuario or not libro_id:
        return jsonify({"error": "Los campos 'usuario' y 'libro_id' son obligatorios"}), 400

    # 1. Realizar llamada HTTP a Catálogo para descontar disponibilidad
    catalogo_patch_url = f"{CATALOGO_URL.rstrip('/')}/libros/{libro_id}/disponibilidad"
    try:
        response = requests.patch(catalogo_patch_url, json={"operacion": "descontar"}, timeout=5)
        if response.status_code == 409:
            return jsonify({"error": "El libro no se encuentra disponible"}), 409
        elif response.status_code != 200:
            return jsonify({
                "error": "Error al comunicar con el catálogo de libros",
                "detalle": response.json() if response.headers.get('content-type') == 'application/json' else response.text
            }), response.status_code
    except requests.RequestException as e:
        logger.error(f"Error conectando con Catálogo: {e}")
        return jsonify({"error": "No se pudo establecer comunicación con el servicio de Catálogo"}), 503

    # 2. Calcular fechas y registrar préstamo localmente
    fecha_actual_dt = datetime.now()
    fecha_limite_dt = fecha_actual_dt + timedelta(days=DIAS_PRESTAMO)
    
    fecha_prestamo_str = fecha_actual_dt.isoformat()
    fecha_limite_str = fecha_limite_dt.isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO prestamos (usuario, libro_id, fecha_prestamo, fecha_limite, estado)
            VALUES (?, ?, ?, ?, 'ACTIVO')
            """,
            (usuario, libro_id, fecha_prestamo_str, fecha_limite_str)
        )
        conn.commit()
        prestamo_id = cursor.lastrowid

        cursor.execute("SELECT * FROM prestamos WHERE id = ?", (prestamo_id,))
        prestamo = dict(cursor.fetchone())
        conn.close()

        return jsonify(prestamo), 201

    except Exception as e:
        logger.error(f"Error al guardar préstamo localmente. Iniciando rollback en Catálogo: {e}")
        conn.rollback()
        conn.close()
        
        # Rollback en Catálogo reponiendo el stock
        try:
            requests.patch(catalogo_patch_url, json={"operacion": "reponer"}, timeout=5)
        except requests.RequestException as rollback_err:
            logger.error(f"Error durante el rollback de stock en Catálogo: {rollback_err}")

        return jsonify({"error": "Error interno al procesar el préstamo. Se ha revertido la reserva del libro."}), 500

@app.route('/prestamos', methods=['GET'])
def listar_prestamos():
    usuario_filter = request.args.get('usuario')
    conn = get_db_connection()
    cursor = conn.cursor()

    if usuario_filter:
        cursor.execute("SELECT * FROM prestamos WHERE usuario = ?", (usuario_filter,))
    else:
        cursor.execute("SELECT * FROM prestamos")

    prestamos = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(prestamos), 200

@app.route('/prestamos/<int:prestamo_id>/devolucion', methods=['PUT'])
def registrar_devolucion(prestamo_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM prestamos WHERE id = ?", (prestamo_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Préstamo no encontrado"}), 404

    prestamo = dict(row)
    if prestamo['estado'] != 'ACTIVO':
        conn.close()
        return jsonify({"error": f"El préstamo ya se encuentra en estado '{prestamo['estado']}'"}), 400

    fecha_devolucion_dt = datetime.now()
    fecha_devolucion_str = fecha_devolucion_dt.isoformat()
    fecha_limite_dt = parse_date(prestamo['fecha_limite'])

    # 1. Reponer disponibilidad en servicio Catálogo
    libro_id = prestamo['libro_id']
    catalogo_patch_url = f"{CATALOGO_URL.rstrip('/')}/libros/{libro_id}/disponibilidad"
    try:
        response = requests.patch(catalogo_patch_url, json={"operacion": "reponer"}, timeout=5)
        if response.status_code != 200:
            logger.warning(f"Respuesta inesperada al reponer libro {libro_id} en Catálogo: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Error comunicando reposición a Catálogo para libro {libro_id}: {e}")

    # 2. Actualizar estado del préstamo
    cursor.execute(
        """
        UPDATE prestamos
        SET fecha_devolucion = ?, estado = 'DEVUELTO'
        WHERE id = ?
        """,
        (fecha_devolucion_str, prestamo_id)
    )

    # 3. Verificar si hay mora y calcular multa
    multa_info = None
    dias_retraso = (fecha_devolucion_dt.date() - fecha_limite_dt.date()).days

    if dias_retraso > 0:
        monto_multa = dias_retraso * MULTA_POR_DIA
        cursor.execute(
            """
            INSERT INTO multas (prestamo_id, dias_retraso, monto, estado)
            VALUES (?, ?, ?, 'PENDIENTE')
            """,
            (prestamo_id, dias_retraso, monto_multa)
        )
        multa_id = cursor.lastrowid
        multa_info = {
            "id": multa_id,
            "prestamo_id": prestamo_id,
            "dias_retraso": dias_retraso,
            "monto": monto_multa,
            "estado": "PENDIENTE"
        }

        # 4. Notificar multa (Tolerancia a fallos con timeout corto de 3s)
        notif_url = f"{NOTIFICACIONES_URL.rstrip('/')}/notificar"
        mensaje_notif = (
            f"Estimado/a {prestamo['usuario']}, su devolución del préstamo #{prestamo_id} registró "
            f"{dias_retraso} días de retraso. Se ha generado una multa de ${monto_multa:.2f}."
        )
        try:
            requests.post(
                notif_url,
                json={
                    "tipo": "MULTA",
                    "usuario": prestamo['usuario'],
                    "mensaje": mensaje_notif
                },
                timeout=3
            )
        except requests.RequestException as err:
            logger.error(f"Fallo al enviar notificación de multa para usuario {prestamo['usuario']}: {err}")

    conn.commit()

    cursor.execute("SELECT * FROM prestamos WHERE id = ?", (prestamo_id,))
    prestamo_actualizado = dict(cursor.fetchone())
    conn.close()

    respuesta = {
        "mensaje": "Devolución registrada exitosamente",
        "prestamo": prestamo_actualizado
    }
    if multa_info:
        respuesta["multa"] = multa_info

    return jsonify(respuesta), 200

@app.route('/prestamos/revisar-vencimientos', methods=['POST'])
def revisar_vencimientos():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM prestamos WHERE estado = 'ACTIVO'")
    prestamos_activos = [dict(row) for row in cursor.fetchall()]
    conn.close()

    ahora = datetime.now().date()
    notificaciones_enviadas = 0

    notif_url = f"{NOTIFICACIONES_URL.rstrip('/')}/notificar"

    for prestamo in prestamos_activos:
        fecha_limite_dt = parse_date(prestamo['fecha_limite'])
        if not fecha_limite_dt:
            continue

        dias_restantes = (fecha_limite_dt.date() - ahora).days

        if dias_restantes <= DIAS_AVISO:
            mensaje = (
                f"RECORDATORIO: El préstamo #{prestamo['id']} (Libro ID #{prestamo['libro_id']}) "
                f"vence el {fecha_limite_dt.strftime('%Y-%m-%d')}. Días restantes: {dias_restantes}."
            )
            payload = {
                "tipo": "POR_VENCER",
                "usuario": prestamo['usuario'],
                "mensaje": mensaje
            }

            try:
                resp = requests.post(notif_url, json=payload, timeout=3)
                if resp.status_code in [200, 202]:
                    notificaciones_enviadas += 1
            except requests.RequestException as err:
                logger.error(f"Error enviando notificación por vencer para préstamo #{prestamo['id']}: {err}")

    return jsonify({
        "status": "Revisión de vencimientos completada",
        "prestamos_revisados": len(prestamos_activos),
        "notificaciones_enviadas": notificaciones_enviadas
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8002, debug=True)
