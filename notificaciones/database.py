import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/data/notificaciones.db")

def get_db_connection():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            usuario TEXT NOT NULL,
            mensaje TEXT NOT NULL,
            fecha_creacion TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
