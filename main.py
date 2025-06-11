import tkinter as tk
from tkinter import ttk, messagebox
from dispositivo import Dispositivo, DispositivoDAO
from backup_manager import BackupManager
import threading
import ttkbootstrap as tb  # <- NUEVO

class BackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Backups de Red")
        self.root.geometry("1000x600")
        
        self.dao = DispositivoDAO()
        self.backup_manager = BackupManager()
        
        self.setup_ui()
        self.cargar_dispositivos()

    def setup_ui(self):
        estilo = tb.Style("litera")  # <- TEMA MÁS MODERNO

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.LabelFrame(main_frame, text="Dispositivos", padding=10)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(list_frame, columns=('Nombre', 'IP', 'Tipo', 'Frecuencia'), show='headings', height=20)
        for col in ('Nombre', 'IP', 'Tipo', 'Frecuencia'):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        for text, cmd in [
            ("Agregar", self.mostrar_formulario),
            ("Editar", self.editar_dispositivo),
            ("Eliminar", self.eliminar_dispositivo),
            ("Backup", self.realizar_backup_seleccionado)
        ]:
            ttk.Button(btn_frame, text=text, command=cmd).pack(side=tk.LEFT, padx=5, pady=5)

        form_frame = ttk.LabelFrame(main_frame, text="Formulario de Dispositivo", padding=10)
        form_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        campos = [
            ("Nombre", "nombre_entry"),
            ("IP", "ip_entry"),
            ("Usuario", "usuario_entry"),
            ("Contraseña", "contraseña_entry"),
            ("Tipo", "tipo_combobox", ["Router", "Switch", "Firewall", "Otro"]),
            ("Frecuencia de Backup", "frecuencia_combobox", ["Diario", "Semanal", "Mensual", "Manual"])
        ]

        self.campos = {}

        for idx, (label, name, *extra) in enumerate(campos):
            ttk.Label(form_frame, text=label + ":").grid(row=idx, column=0, sticky=tk.W, pady=4)
            if name.endswith("combobox"):
                cb = ttk.Combobox(form_frame, values=extra[0], state="readonly")
                cb.grid(row=idx, column=1, sticky=tk.EW, pady=4)
                self.campos[name] = cb
            else:
                entry = ttk.Entry(form_frame, show="*" if "contraseña" in name else None)
                entry.grid(row=idx, column=1, sticky=tk.EW, pady=4)
                self.campos[name] = entry

        form_frame.columnconfigure(1, weight=1)

        action_frame = ttk.Frame(form_frame)
        action_frame.grid(row=len(campos), column=0, columnspan=2, pady=10)
        ttk.Button(action_frame, text="Guardar", command=self.guardar_dispositivo).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Cancelar", command=self.limpiar_formulario).pack(side=tk.LEFT, padx=5)

        log_frame = ttk.LabelFrame(self.root, text="Registro de Actividades", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.log_text = tk.Text(log_frame, height=6, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def cargar_dispositivos(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        dispositivos = self.dao.obtener_todos()
        for d in dispositivos:
            self.tree.insert('', tk.END, values=(d.nombre, d.ip, d.tipo, d.frecuencia_backup), iid=d.id)

    def mostrar_formulario(self, dispositivo=None):
        self.limpiar_formulario()
        self.dispositivo_actual = None
        if dispositivo:
            self.campos['nombre_entry'].insert(0, dispositivo.nombre)
            self.campos['ip_entry'].insert(0, dispositivo.ip)
            self.campos['usuario_entry'].insert(0, dispositivo.usuario)
            self.campos['contraseña_entry'].insert(0, dispositivo.contraseña)
            self.campos['tipo_combobox'].set(dispositivo.tipo)
            self.campos['frecuencia_combobox'].set(dispositivo.frecuencia_backup)
            self.dispositivo_actual = dispositivo

    def limpiar_formulario(self):
        for widget in self.campos.values():
            widget.delete(0, tk.END) if isinstance(widget, ttk.Entry) else widget.set('')

    def guardar_dispositivo(self):
        try:
            nombre = self.campos['nombre_entry'].get()
            ip = self.campos['ip_entry'].get()
            usuario = self.campos['usuario_entry'].get()
            contraseña = self.campos['contraseña_entry'].get()
            tipo = self.campos['tipo_combobox'].get()
            frecuencia = self.campos['frecuencia_combobox'].get()
            if not all([nombre, ip, usuario, contraseña, tipo, frecuencia]):
                raise ValueError("Todos los campos son obligatorios")

            dispositivo = Dispositivo(nombre=nombre, ip=ip, usuario=usuario, contraseña=contraseña,
                                      tipo=tipo, frecuencia_backup=frecuencia)

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
        self.mostrar_formulario(dispositivo)

    def eliminar_dispositivo(self):
        seleccionado = self.tree.selection()
        if not seleccionado:
            return messagebox.showwarning("Advertencia", "Seleccione un dispositivo para eliminar")
        dispositivo = self.dao.obtener_por_id(int(seleccionado[0]))
        if messagebox.askyesno("Confirmar", f"Eliminar {dispositivo.nombre}?"):
            self.dao.eliminar(dispositivo.id)
            self.log(f"Dispositivo eliminado: {dispositivo.nombre}")
            self.cargar_dispositivos()

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
    root = tb.Window(themename="litera")  # <- NUEVO uso de ttkbootstrap
    app = BackupApp(root)
    root.mainloop()
