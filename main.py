import tkinter as tk
from tkinter import ttk, messagebox
from dispositivo import Dispositivo, DispositivoDAO
from backup_manager import BackupManager
import threading
import ttkbootstrap as tb
import paramiko
import time
from PIL import Image, ImageTk

class BackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Backups de Red")
        self.root.state('zoomed')  # Abrir en pantalla completa

        self.dao = DispositivoDAO()
        self.backup_manager = BackupManager()
        self.dispositivo_actual = None

        self.setup_ui()
        self.cargar_dispositivos()

    def setup_ui(self):
        estilo = tb.Style("flatly")

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.LabelFrame(main_frame, text="Dispositivos Registrados", padding=10, style="info.TLabelframe")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(list_frame, columns=('Nombre', 'IP', 'Puerto', 'Tipo', 'Frecuencia'), show='headings', height=15)
        for col, anchor in [('Nombre', 'w'), ('IP', 'center'), ('Puerto', 'center'), ('Tipo', 'center'), ('Frecuencia', 'center')]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor=anchor, width=100)
        self.tree.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        action_buttons = [
            ("✏️ Editar", self.editar_dispositivo),
            ("🗑️ Eliminar", self.eliminar_dispositivo),
            ("💾 Backup", self.realizar_backup_seleccionado),
            ("🔍 Probar SSH", self.probar_conexion_ssh)
        ]

        for text, cmd in action_buttons:
            btn = ttk.Button(btn_frame, text=text, command=cmd, width=14, style="success.TButton")
            btn.pack(side=tk.LEFT, padx=5, pady=5)

        form_frame = ttk.LabelFrame(main_frame, text="Gestión de Dispositivo", padding=10, style="info.TLabelframe")
        form_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        campos = [
            ("Nombre", "nombre_entry"),
            ("Dirección IP", "ip_entry"),
            ("Usuario", "usuario_entry"),
            ("Contraseña", "contraseña_entry"),
            ("Puerto SSH", "puerto_entry"),
            ("Tipo", "tipo_combobox", ["Router", "Switch", "Firewall", "Servidor", "Otro"]),
            ("Frecuencia Backup", "frecuencia_combobox", ["Diario", "Semanal", "Mensual", "Manual"])
        ]

        self.campos = {}
        for idx, (label, name, *extra) in enumerate(campos):
            ttk.Label(form_frame, text=label + ":").grid(row=idx, column=0, sticky=tk.W, pady=3, padx=5)
            if name.endswith("combobox"):
                cb = ttk.Combobox(form_frame, values=extra[0], state="readonly")
                cb.grid(row=idx, column=1, sticky=tk.EW, pady=3, padx=5)
                self.campos[name] = cb
            else:
                show = "*" if "contraseña" in name else None
                default = "22" if "puerto" in name else ""
                entry = ttk.Entry(form_frame, show=show)
                entry.insert(0, default)
                entry.grid(row=idx, column=1, sticky=tk.EW, pady=3, padx=5)
                self.campos[name] = entry

        form_frame.columnconfigure(1, weight=1)

        action_frame = ttk.Frame(form_frame)
        action_frame.grid(row=len(campos)+1, column=0, columnspan=2, pady=10)
        ttk.Button(action_frame, text="💾 Guardar", command=self.guardar_dispositivo, width=12, style="primary.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="✖ Cancelar", command=self.limpiar_formulario, width=12, style="danger.TButton").pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(self.root, text="Registro de Actividades", padding=10, style="primary.TLabelframe")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

        self.log_text = tk.Text(log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD, bg="#f8f9fa", font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def cargar_dispositivos(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        dispositivos = self.dao.obtener_todos()
        for d in dispositivos:
            self.tree.insert('', tk.END, values=(d.nombre, d.ip, d.puerto_ssh, d.tipo, d.frecuencia_backup), iid=d.id)

    def mostrar_formulario(self, dispositivo=None):
        self.limpiar_formulario()
        self.dispositivo_actual = dispositivo
        if dispositivo:
            self.campos['nombre_entry'].insert(0, dispositivo.nombre)
            self.campos['ip_entry'].insert(0, dispositivo.ip)
            self.campos['usuario_entry'].insert(0, dispositivo.usuario)
            self.campos['contraseña_entry'].insert(0, dispositivo.contraseña)
            self.campos['puerto_entry'].insert(0, str(dispositivo.puerto_ssh))
            self.campos['tipo_combobox'].set(dispositivo.tipo)
            self.campos['frecuencia_combobox'].set(dispositivo.frecuencia_backup)

    def limpiar_formulario(self):
        for widget in self.campos.values():
            if isinstance(widget, ttk.Entry):
                widget.delete(0, tk.END)
                if "puerto" in str(widget):
                    widget.insert(0, "22")
            else:
                widget.set('')
        self.dispositivo_actual = None

    def guardar_dispositivo(self):
        try:
            nombre = self.campos['nombre_entry'].get().strip()
            ip = self.campos['ip_entry'].get().strip()
            usuario = self.campos['usuario_entry'].get().strip()
            contraseña = self.campos['contraseña_entry'].get()
            puerto = int(self.campos['puerto_entry'].get() or 22)
            tipo = self.campos['tipo_combobox'].get()
            frecuencia = self.campos['frecuencia_combobox'].get()

            if not all([nombre, ip, usuario, tipo, frecuencia]):
                raise ValueError("Todos los campos son obligatorios")
            if not 1 <= puerto <= 65535:
                raise ValueError("Puerto debe estar entre 1 y 65535")

            dispositivo = Dispositivo(nombre=nombre, ip=ip, usuario=usuario, contraseña=contraseña, tipo=tipo, frecuencia_backup=frecuencia, puerto_ssh=puerto)

            if self.dispositivo_actual:
                dispositivo.id = self.dispositivo_actual.id
                self.dao.actualizar(dispositivo)
                self.log(f"Dispositivo actualizado: {nombre} ({ip}:{puerto})")
            else:
                self.dao.guardar(dispositivo)
                self.log(f"Dispositivo agregado: {nombre} ({ip}:{puerto})")

            self.cargar_dispositivos()
            self.limpiar_formulario()

        except ValueError as e:
            messagebox.showerror("Error de validación", str(e))
        except Exception as e:
            messagebox.showerror("Error inesperado", f"Ocurrió un error: {str(e)}")

    def editar_dispositivo(self):
        if seleccionado := self.tree.selection():
            dispositivo = self.dao.obtener_por_id(int(seleccionado[0]))
            self.mostrar_formulario(dispositivo)
        else:
            messagebox.showwarning("Selección requerida", "Por favor seleccione un dispositivo de la lista")

    def eliminar_dispositivo(self):
        if seleccionado := self.tree.selection():
            dispositivo = self.dao.obtener_por_id(int(seleccionado[0]))
            if messagebox.askyesno("Confirmar eliminación", f"¿Está seguro de eliminar el dispositivo:\n\n{dispositivo.nombre} ({dispositivo.ip})?", icon='warning'):
                self.dao.eliminar(dispositivo.id)
                self.log(f"Dispositivo eliminado: {dispositivo.nombre}")
                self.cargar_dispositivos()
        else:
            messagebox.showwarning("Selección requerida", "Por favor seleccione un dispositivo de la lista")

    def realizar_backup_seleccionado(self):
        if seleccionado := self.tree.selection():
            dispositivo = self.dao.obtener_por_id(int(seleccionado[0]))
            self.log(f"Iniciando backup de {dispositivo.nombre}...")
            threading.Thread(target=self._realizar_backup, args=(dispositivo,), daemon=True).start()
        else:
            messagebox.showwarning("Selección requerida", "Por favor seleccione un dispositivo de la lista")

    def _realizar_backup(self, dispositivo):
        try:
            if self.backup_manager.realizar_backup(dispositivo):
                self.log(f"✓ Backup completado: {dispositivo.nombre}")
            else:
                self.log(f"✗ Falló backup: {dispositivo.nombre}")
        except Exception as e:
            self.log(f"⚠ Error durante backup: {str(e)}")

    def probar_conexion_ssh(self):
        if seleccionado := self.tree.selection():
            dispositivo = self.dao.obtener_por_id(int(seleccionado[0]))
            self.log(f"Probando conexión SSH a {dispositivo.nombre}...")
            threading.Thread(target=self._probar_conexion_ssh, args=(dispositivo,), daemon=True).start()
        else:
            messagebox.showwarning("Selección requerida", "Por favor seleccione un dispositivo de la lista")

    def _probar_conexion_ssh(self, dispositivo):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=dispositivo.ip, port=dispositivo.puerto_ssh, username=dispositivo.usuario, password=dispositivo.contraseña, timeout=5, look_for_keys=False, allow_agent=False)
            ssh.close()
            self.log(f"✓ Conexión SSH exitosa: {dispositivo.nombre} ({dispositivo.ip}:{dispositivo.puerto_ssh})")
        except Exception as e:
            self.log(f"✗ Falló conexión SSH: {str(e)}")

    def log(self, mensaje):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, mensaje + "\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)

def mostrar_splash(root):
    splash = tk.Toplevel()
    splash.overrideredirect(True)
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    splash.geometry(f"{screen_width}x{screen_height}+0+0")
    splash.configure(bg="white")

    img = Image.open("logo.png")
    img = img.resize((500, 500), Image.Resampling.LANCZOS)
    logo = ImageTk.PhotoImage(img)
    splash.logo = logo  # 👈 evita que se elimine la imagen

    tk.Label(splash, image=logo, bg="white").place(relx=0.5, rely=0.35, anchor=tk.CENTER)
    tk.Label(splash, text="Cargando RedSafe...", font=("Segoe UI", 18, "bold"), bg="white").place(relx=0.5, rely=0.6, anchor=tk.CENTER)

    progress = ttk.Progressbar(splash, mode='indeterminate', length=200)
    progress.place(relx=0.5, rely=0.7, anchor=tk.CENTER)
    progress.start()

    def cerrar_y_mostrar():
        splash.destroy()
        app = BackupApp(root)  # ← Aquí recién creamos la app
        root.deiconify()

    # Esperar 2 segundos (2000 milisegundos)
    splash.after(2000, cerrar_y_mostrar)


if __name__ == "__main__":
    root = tb.Window(themename="flatly")
    root.state('zoomed')
    root.withdraw()
    mostrar_splash(root)
    root.mainloop()
