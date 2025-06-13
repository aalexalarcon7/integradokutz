import sqlite3
from dataclasses import dataclass

@dataclass
class Dispositivo:
    id: int = None
    nombre: str = ""
    ip: str = ""
    usuario: str = ""
    contraseña: str = ""
    tipo: str = ""
    frecuencia_backup: str = ""
    puerto_ssh: int = 22  # Nuevo campo con valor por defecto 22

class DispositivoDAO:
    def __init__(self, db_path='dispositivos.db'):
        self.db_path = db_path
        self._crear_tabla()
    
    def _crear_tabla(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS dispositivos (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                nombre TEXT NOT NULL,
                                ip TEXT NOT NULL,
                                usuario TEXT NOT NULL,
                                contraseña TEXT NOT NULL,
                                tipo TEXT NOT NULL,
                                frecuencia_backup TEXT NOT NULL,
                                puerto_ssh INTEGER NOT NULL DEFAULT 22
                              )''')
            conn.commit()
    
    def guardar(self, dispositivo):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO dispositivos 
                              (nombre, ip, usuario, contraseña, tipo, frecuencia_backup, puerto_ssh)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (dispositivo.nombre, dispositivo.ip, dispositivo.usuario,
                            dispositivo.contraseña, dispositivo.tipo, 
                            dispositivo.frecuencia_backup, dispositivo.puerto_ssh))
            dispositivo.id = cursor.lastrowid
            conn.commit()
    
    def actualizar(self, dispositivo):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''UPDATE dispositivos SET
                                nombre = ?,
                                ip = ?,
                                usuario = ?,
                                contraseña = ?,
                                tipo = ?,
                                frecuencia_backup = ?,
                                puerto_ssh = ?
                              WHERE id = ?''',
                           (dispositivo.nombre, dispositivo.ip, dispositivo.usuario,
                            dispositivo.contraseña, dispositivo.tipo,
                            dispositivo.frecuencia_backup, dispositivo.puerto_ssh,
                            dispositivo.id))
            conn.commit()
    
    def eliminar(self, dispositivo_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM dispositivos WHERE id = ?', (dispositivo_id,))
            conn.commit()
    
    def obtener_por_id(self, dispositivo_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM dispositivos WHERE id = ?', (dispositivo_id,))
            row = cursor.fetchone()
            
            if row:
                return Dispositivo(
                    id=row[0],
                    nombre=row[1],
                    ip=row[2],
                    usuario=row[3],
                    contraseña=row[4],
                    tipo=row[5],
                    frecuencia_backup=row[6],
                    puerto_ssh=row[7]  # Nuevo campo
                )
            return None
    
    def obtener_todos(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM dispositivos')
            rows = cursor.fetchall()
            
            dispositivos = []
            for row in rows:
                dispositivos.append(Dispositivo(
                    id=row[0],
                    nombre=row[1],
                    ip=row[2],
                    usuario=row[3],
                    contraseña=row[4],
                    tipo=row[5],
                    frecuencia_backup=row[6],
                    puerto_ssh=row[7]  # Nuevo campo
                ))
            return dispositivos
