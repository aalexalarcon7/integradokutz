import paramiko
import os
from datetime import datetime, timedelta
import logging
from dispositivo import Dispositivo

class BackupManager:
    def __init__(self):
        self.backup_dir = "backups"
        self._crear_directorio_backup()
        logging.basicConfig(
            filename='backup.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _crear_directorio_backup(self):
        """Crea el directorio de backups si no existe"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            self._log("Directorio de backups creado")
    
    def _generar_nombre_backup(self, dispositivo: Dispositivo) -> str:
        """Genera un nombre de archivo único para el backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_limpio = "".join(c if c.isalnum() else "_" for c in dispositivo.nombre)
        return os.path.join(
            self.backup_dir,
            f"backup_{nombre_limpio}_{timestamp}.cfg"
        )
    
    def _obtener_comando_backup(self, dispositivo: Dispositivo) -> str:
        """Devuelve el comando adecuado según el tipo de dispositivo"""
        comandos = {
            "Router": "/export compact" if "mikrotik" in dispositivo.nombre.lower() else "show running-config",
            "Switch": "show running-config",
            "Firewall": "show configuration",
            "Servidor": "cat /etc/network/interfaces",
            "Otro": "show configuration"
        }
        return comandos.get(dispositivo.tipo, "show running-config")
    
    def _ejecutar_comando_ssh(self, ssh, comando: str) -> str:
        """Ejecuta un comando remoto via SSH y devuelve la salida"""
        stdin, stdout, stderr = ssh.exec_command(comando)
        salida = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        if error and not salida:
            raise Exception(f"Error en comando: {error.strip()}")
        return salida
    
    def realizar_backup(self, dispositivo: Dispositivo) -> bool:
        """
        Realiza el backup de la configuración del dispositivo via SSH
        Devuelve True si fue exitoso, False si falló
        """
        try:
            self._log(f"Iniciando backup de {dispositivo.nombre} ({dispositivo.ip}:{dispositivo.puerto_ssh})...")
            
            # Configuración de conexión SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Conexión al dispositivo
            ssh.connect(
                hostname=dispositivo.ip,
                port=dispositivo.puerto_ssh,
                username=dispositivo.usuario,
                password=dispositivo.contraseña,
                timeout=15,
                look_for_keys=False,
                allow_agent=False
            )
            
            # Obtener comando específico para el dispositivo
            comando = self._obtener_comando_backup(dispositivo)
            self._log(f"Ejecutando comando: {comando}")
            
            # Ejecutar comando y obtener configuración
            configuracion = self._ejecutar_comando_ssh(ssh, comando)
            
            if not configuracion:
                raise Exception("El comando no devolvió resultados")
            
            # Guardar backup localmente
            archivo_backup = self._generar_nombre_backup(dispositivo)
            with open(archivo_backup, 'w', encoding='utf-8') as f:
                f.write(configuracion)
            
            self._log(f"Backup guardado en: {os.path.abspath(archivo_backup)}")
            
            # Limpiar backups antiguos
            self._limpiar_backups_antiguos(dispositivo)
            
            return True
            
        except paramiko.AuthenticationException:
            self._log(f"Error de autenticación en {dispositivo.nombre}", level="error")
            return False
        except paramiko.SSHException as e:
            self._log(f"Error SSH en {dispositivo.nombre}: {str(e)}", level="error")
            return False
        except Exception as e:
            self._log(f"Error inesperado en {dispositivo.nombre}: {str(e)}", level="error")
            return False
        finally:
            try:
                if 'ssh' in locals():
                    ssh.close()
            except Exception:
                pass
    
    def _limpiar_backups_antiguos(self, dispositivo: Dispositivo, dias_retencion: int = 30) -> None:
        """Elimina backups más antiguos que el período de retención"""
        try:
            prefix = f"backup_{dispositivo.nombre}_"
            fecha_limite = datetime.now() - timedelta(days=dias_retencion)
            
            for archivo in os.listdir(self.backup_dir):
                if archivo.startswith(prefix):
                    ruta_completa = os.path.join(self.backup_dir, archivo)
                    fecha_archivo = datetime.fromtimestamp(os.path.getctime(ruta_completa))
                    
                    if fecha_archivo < fecha_limite:
                        os.remove(ruta_completa)
                        self._log(f"Eliminado backup antiguo: {archivo}")
        except Exception as e:
            self._log(f"Error limpiando backups: {str(e)}", level="error")
    
    def _log(self, mensaje: str, level: str = "info") -> None:
        """Registra mensajes en log y consola"""
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(mensaje)
        
        # Formato especial para consola
        if level == "error":
            print(f"[!] {mensaje}")
        else:
            print(f"[*] {mensaje}")
            
