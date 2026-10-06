import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/data/catalogo.db")

def get_db_connection():
    # Ensure directory exists before connecting
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
        CREATE TABLE IF NOT EXISTS autores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            nacionalidad TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS libros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            autor_id INTEGER,
            ejemplares_totales INTEGER NOT NULL DEFAULT 1,
            ejemplares_disponibles INTEGER NOT NULL DEFAULT 1,
            estado TEXT NOT NULL DEFAULT 'DISPONIBLE',
            FOREIGN KEY (autor_id) REFERENCES autores (id) ON DELETE SET NULL
        )
    ''')
    
    conn.commit()
    conn.close()
