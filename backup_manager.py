import paramiko
import os
from datetime import datetime, timedelta
import logging

class BackupManager:
    def __init__(self):
        self.backup_dir = "backups"
        self._crear_directorio_backup()
        logging.basicConfig(filename='backup.log', level=logging.INFO)
    
    def _crear_directorio_backup(self):
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def _generar_nombre_backup(self, dispositivo):
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.backup_dir, f"backup_{dispositivo.nombre}_{fecha}.cfg")
    
    def _obtener_comando_backup(self, tipo_dispositivo):
        # Comandos específicos por tipo de dispositivo
        comandos = {
            "Router": "show running-config",
            "Switch": "show running-config",
            "Firewall": "show configuration",
            # Agregar más según necesidad
        }
        return comandos.get(tipo_dispositivo, "show running-config")
    
    def realizar_backup(self, dispositivo):
        try:
            # Establecer conexión SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self._log(f"Conectando a {dispositivo.nombre} ({dispositivo.ip})...")
            ssh.connect(
                hostname=dispositivo.ip,
                username=dispositivo.usuario,
                password=dispositivo.contraseña,
                timeout=10
            )
            
            # Ejecutar comando de backup
            comando = self._obtener_comando_backup(dispositivo.tipo)
            self._log(f"Ejecutando comando: {comando}")
            stdin, stdout, stderr = ssh.exec_command(comando)
            config = stdout.read().decode()
            
            if not config:
                error = stderr.read().decode()
                self._log(f"Error al obtener configuración: {error}")
                return False
            
            # Guardar archivo localmente
            archivo_backup = self._generar_nombre_backup(dispositivo)
            with open(archivo_backup, 'w') as f:
                f.write(config)
            
            self._log(f"Backup guardado en: {archivo_backup}")
            
            # Limpiar backups antiguos
            self._limpiar_backups_antiguos(dispositivo)
            
            return True
            
        except paramiko.AuthenticationException:
            self._log(f"Error de autenticación en {dispositivo.nombre}")
            return False
        except paramiko.SSHException as e:
            self._log(f"Error SSH en {dispositivo.nombre}: {str(e)}")
            return False
        except Exception as e:
            self._log(f"Error inesperado en {dispositivo.nombre}: {str(e)}")
            return False
        finally:
            try:
                ssh.close()
            except:
                pass
    
    def _limpiar_backups_antiguos(self, dispositivo):
        seis_meses = datetime.now() - timedelta(days=180)
        prefix = f"backup_{dispositivo.nombre}_"
        
        for archivo in os.listdir(self.backup_dir):
            if archivo.startswith(prefix):
                ruta_archivo = os.path.join(self.backup_dir, archivo)
                fecha_creacion = datetime.fromtimestamp(os.path.getctime(ruta_archivo))
                
                if fecha_creacion < seis_meses:
                    try:
                        os.remove(ruta_archivo)
                        self._log(f"Eliminado backup antiguo: {archivo}")
                    except Exception as e:
                        self._log(f"Error al eliminar {archivo}: {str(e)}")
    
    def _log(self, mensaje):
        logging.info(f"{datetime.now()}: {mensaje}")
        print(mensaje)  # También mostrar en consola