import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "biomini_local.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si el esquema es antiguo (si no tiene la columna 'id')
    try:
        cursor.execute("PRAGMA table_info(huellas_locales)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and "id" not in columns:
            print("⚠️ Esquema antiguo detectado en huellas_locales. Recreando tabla...")
            cursor.execute("DROP TABLE huellas_locales")
    except Exception as e:
        print(f"⚠️ Error al verificar esquema de huellas_locales: {e}")
    
    # Tabla para almacenar huellas mapeadas por trabajador_id
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS huellas_locales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trabajador_id INTEGER NOT NULL,
        huella_template BLOB NOT NULL
    )
    """)
    
    # Tabla para almacenar asistencias en modo contingencia (offline)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contingencia_asistencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trabajador_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()
    print("💾 Base de datos SQLite local inicializada correctamente.")

def save_huella_local(trabajador_id: int, huella_bytes: bytes):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO huellas_locales (trabajador_id, huella_template)
    VALUES (?, ?)
    """, (trabajador_id, huella_bytes))
    conn.commit()
    conn.close()

def clear_huellas_locales():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM huellas_locales")
    conn.commit()
    conn.close()
    print("🧹 Caché local de huellas vaciada.")

def get_all_huellas_locales():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT trabajador_id, huella_template FROM huellas_locales")
    rows = cursor.fetchall()
    conn.close()
    return [(row['trabajador_id'], row['huella_template']) for row in rows]

def save_asistencia_offline(trabajador_id: int, fecha: str, hora: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO contingencia_asistencias (trabajador_id, fecha, hora)
    VALUES (?, ?, ?)
    """, (trabajador_id, fecha, hora))
    conn.commit()
    conn.close()

def get_asistencias_offline():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT trabajador_id, fecha, hora FROM contingencia_asistencias")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "trabajador_id": row["trabajador_id"],
            "fecha": row["fecha"],
            "hora": row["hora"]
        } for row in rows
    ]

def clear_asistencias_offline():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contingencia_asistencias")
    conn.commit()
    conn.close()
    print("🧹 Base de datos de contingencia local limpiada.")
