import tkinter as tk
from tkinter import ttk, messagebox
from dispositivo import Dispositivo, DispositivoDAO
from backup_manager import BackupManager
import threading
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import paramiko  

class BackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestión de Dispositivos de Red")
        self.root.geometry("1000x700")
        
        self.dao = DispositivoDAO()
        self.backup_manager = BackupManager()
        self.dispositivo_actual = None
        
        self.setup_ui()
        self.cargar_dispositivos()

    def setup_ui(self):
        estilo = tb.Style("litera")

        # Frame principal
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Sección de formulario
        form_frame = ttk.LabelFrame(main_frame, text="Gestión de Dispositivos", padding=10)
        form_frame.pack(fill=tk.X, pady=5, padx=5)

        # Campos del formulario
        ttk.Label(form_frame, text="Nombre:").grid(row=0, column=0, sticky=tk.W, pady=4, padx=5)
        self.nombre_entry = ttk.Entry(form_frame)
        self.nombre_entry.grid(row=0, column=1, sticky=tk.EW, pady=4, padx=5)

        ttk.Label(form_frame, text="IP:").grid(row=0, column=2, sticky=tk.W, pady=4, padx=5)
        self.ip_entry = ttk.Entry(form_frame)
        self.ip_entry.grid(row=0, column=3, sticky=tk.EW, pady=4, padx=5)

        ttk.Label(form_frame, text="Tipo:").grid(row=1, column=0, sticky=tk.W, pady=4, padx=5)
        self.tipo_combobox = ttk.Combobox(form_frame, values=["Router", "Switch", "Firewall", "Ubikiti", "Otro"], state="readonly")
        self.tipo_combobox.grid(row=1, column=1, sticky=tk.EW, pady=4, padx=5)

        ttk.Label(form_frame, text="Usuario:").grid(row=2, column=0, sticky=tk.W, pady=4, padx=5)
        self.usuario_entry = ttk.Entry(form_frame)
        self.usuario_entry.grid(row=2, column=1, sticky=tk.EW, pady=4, padx=5)

        ttk.Label(form_frame, text="Contraseña:").grid(row=2, column=2, sticky=tk.W, pady=4, padx=5)
        self.contraseña_entry = ttk.Entry(form_frame, show="*")
        self.contraseña_entry.grid(row=2, column=3, sticky=tk.EW, pady=4, padx=5)

        ttk.Label(form_frame, text="Puerto SSH:").grid(row=1, column=2, sticky=tk.W, pady=4, padx=5)
        self.puerto_entry = ttk.Entry(form_frame)
        self.puerto_entry.insert(0, "22")
        self.puerto_entry.grid(row=1, column=3, sticky=tk.EW, pady=4, padx=5)

        # Botones de acción
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=10, sticky=tk.EW)
        
        ttk.Button(btn_frame, text="Agregar", command=self.guardar_dispositivo).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Modificar", command=self.editar_dispositivo).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Eliminar", command=self.eliminar_dispositivo).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Probar SSH", command=self.probar_ssh).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Cargar", command=self.cargar_dispositivos).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(btn_frame, text="Hacer Backup", command=self.realizar_backup_seleccionado).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Tabla de dispositivos registrados
        table_frame = ttk.LabelFrame(main_frame, text="Dispositivos Registrados", padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

        columns = ('ID', 'Nombre', 'IP', 'Usuario', 'Tipo', 'Puerto SSH')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor=tk.CENTER, width=100)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Área de registro
        log_frame = ttk.LabelFrame(main_frame, text="Registro de Actividades", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        self.log_text = tk.Text(log_frame, height=6, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def cargar_dispositivos(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        dispositivos = self.dao.obtener_todos()
        for d in dispositivos:
            self.tree.insert('', tk.END, values=(
                d.id, d.nombre, d.ip, d.usuario, d.tipo, d.puerto_ssh
            ))

    def limpiar_formulario(self):
        self.nombre_entry.delete(0, tk.END)
        self.ip_entry.delete(0, tk.END)
        self.usuario_entry.delete(0, tk.END)
        self.contraseña_entry.delete(0, tk.END)
        self.tipo_combobox.set('')
        self.puerto_entry.delete(0, tk.END)
        self.puerto_entry.insert(0, "22")
        self.dispositivo_actual = None

    def guardar_dispositivo(self):
        try:
            nombre = self.nombre_entry.get()
            ip = self.ip_entry.get()
            usuario = self.usuario_entry.get()
            contraseña = self.contraseña_entry.get()
            tipo = self.tipo_combobox.get()
            puerto = self.puerto_entry.get()

            if not all([nombre, ip, usuario, contraseña, tipo, puerto]):
                raise ValueError("Todos los campos son obligatorios")

            dispositivo = Dispositivo(
                nombre=nombre,
                ip=ip,
                usuario=usuario,
                contraseña=contraseña,
                tipo=tipo,
                puerto_ssh=int(puerto)
            )

            if self.dispositivo_actual:
                dispositivo.id = self.dispositivo_actual.id
                self.dao.actualizar(dispositivo)
                self.log(f"Dispositivo actualizado: {nombre}")
            else:
                self.dao.guardar(dispositivo)
                self.log(f"Dispositivo agregado: {nombre}")

            self.cargar_dispositivos()
            self.limpiar_formulario()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def editar_dispositivo(self):
        seleccionado = self.tree.selection()
        if not seleccionado:
            return messagebox.showwarning("Advertencia", "Seleccione un dispositivo para editar")
        
        dispositivo = self.dao.obtener_por_id(int(seleccionado[0]))
        self.dispositivo_actual = dispositivo
        
        self.nombre_entry.delete(0, tk.END)
        self.nombre_entry.insert(0, dispositivo.nombre)
        
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, dispositivo.ip)
        
        self.usuario_entry.delete(0, tk.END)
        self.usuario_entry.insert(0, dispositivo.usuario)
        
        self.contraseña_entry.delete(0, tk.END)
        self.contraseña_entry.insert(0, dispositivo.contraseña)
        
        self.tipo_combobox.set(dispositivo.tipo)
        
        self.puerto_entry.delete(0, tk.END)
        self.puerto_entry.insert(0, str(dispositivo.puerto_ssh))

    def eliminar_dispositivo(self):
        seleccionado = self.tree.selection()
        if not seleccionado:
            return messagebox.showwarning("Advertencia", "Seleccione un dispositivo para eliminar")
        
        dispositivo = self.dao.obtener_por_id(int(seleccionado[0]))
        if messagebox.askyesno("Confirmar", f"¿Eliminar {dispositivo.nombre}?"):
            self.dao.eliminar(dispositivo.id)
            self.log(f"Dispositivo eliminado: {dispositivo.nombre}")
            self.cargar_dispositivos()

    def probar_ssh(self):
        seleccionado = self.tree.selection()
        if not seleccionado:
            return messagebox.showwarning("Advertencia", "Seleccione un dispositivo para probar SSH")
        
        dispositivo = self.dao.obtener_por_id(int(seleccionado[0]))
        self.log(f"Probando conexión SSH a {dispositivo.nombre} ({dispositivo.ip}:{dispositivo.puerto_ssh})...")
        
        try:
            # Implementar lógica de prueba SSH aquí
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=dispositivo.ip,
                username=dispositivo.usuario,
                password=dispositivo.contraseña,
                port=dispositivo.puerto_ssh,
                timeout=10
            )
            ssh.close()
            self.log(f"✓ Conexión SSH exitosa a {dispositivo.nombre}")
            return True
        except Exception as e:
            self.log(f"✗ Error en conexión SSH: {str(e)}")
            return False

    def realizar_backup_seleccionado(self):
        seleccionado = self.tree.selection()
        if not seleccionado:
            return messagebox.showwarning("Advertencia", "Seleccione un dispositivo para realizar backup")
        
        dispositivo = self.dao.obtener_por_id(int(seleccionado[0]))
        self.log(f"Iniciando backup para {dispositivo.nombre}...")
        threading.Thread(target=self._realizar_backup, args=(dispositivo,), daemon=True).start()

    def _realizar_backup(self, dispositivo):
        try:
            if self.backup_manager.realizar_backup(dispositivo):
                self.log(f"Backup completado para {dispositivo.nombre}")
            else:
                self.log(f"Error en backup para {dispositivo.nombre}")
        except Exception as e:
            self.log(f"Error durante backup: {str(e)}")

    def log(self, mensaje):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{mensaje}\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

if __name__ == "__main__":
    root = tb.Window(themename="litera")
    app = BackupApp(root)
    root.mainloop()