import sys
from datetime import datetime
from flask import Flask, request, jsonify
from database import init_db, get_db_connection

app = Flask(__name__)

with app.app_context():
    init_db()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "UP"}), 200

@app.route('/notificar', methods=['POST'])
def crear_notificacion():
    data = request.get_json() or {}
    tipo = data.get('tipo')
    usuario = data.get('usuario')
    mensaje = data.get('mensaje')

    if not tipo or not usuario or not mensaje:
        return jsonify({"error": "Los campos 'tipo', 'usuario' y 'mensaje' son obligatorios"}), 400

    if tipo not in ['POR_VENCER', 'MULTA']:
        # Se permite flexibilidad pero se registra el tipo recibido
        pass

    fecha_creacion = datetime.now().isoformat()

    # 1. Imprimir alerta en la consola/stdout del contenedor
    print(f"\n================ [ALERTA DE NOTIFICACIÓN] ================", flush=True)
    print(f"Tipo:           {tipo}", flush=True)
    print(f"Usuario:        {usuario}", flush=True)
    print(f"Mensaje:        {mensaje}", flush=True)
    print(f"Fecha Creación: {fecha_creacion}", flush=True)
    print(f"==========================================================\n", flush=True)
    sys.stdout.flush()

    # 2. Registrar evento en la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO notificaciones (tipo, usuario, mensaje, fecha_creacion)
        VALUES (?, ?, ?, ?)
        """,
        (tipo, usuario, mensaje, fecha_creacion)
    )
    conn.commit()
    notif_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "status": "Notificación recibida",
        "id": notif_id
    }), 202

@app.route('/notificaciones', methods=['GET'])
def listar_notificaciones():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notificaciones ORDER BY id DESC")
    notificaciones = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(notificaciones), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8003, debug=True)
