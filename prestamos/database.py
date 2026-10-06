import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/data/prestamos.db")

def get_db_connection():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prestamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            libro_id INTEGER NOT NULL,
            fecha_prestamo TEXT NOT NULL,
            fecha_limite TEXT NOT NULL,
            fecha_devolucion TEXT,
            estado TEXT NOT NULL DEFAULT 'ACTIVO'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS multas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestamo_id INTEGER NOT NULL,
            dias_retraso INTEGER NOT NULL,
            monto REAL NOT NULL,
            estado TEXT NOT NULL DEFAULT 'PENDIENTE',
            FOREIGN KEY (prestamo_id) REFERENCES prestamos (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
