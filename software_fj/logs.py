# =============================================================================
# logs.py — Sistema de registro de eventos para Software FJ
# =============================================================================
# Escribe entradas de log con marca de tiempo en un archivo de texto plano.
# Usa bloques finally para garantizar el cierre correcto del archivo,
# incluso si ocurre un error durante la escritura.
# =============================================================================

import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path


class LogLevel(Enum):
    """Niveles de severidad para las entradas de log."""
    INFO     = "INFO"
    WARNING  = "WARNING"
    ERROR    = "ERROR"
    CRITICAL = "CRITICAL"


class EventLogger:
    """
    Escribe entradas de log con marca de tiempo en un archivo de texto plano.

    Uso:
        logger = EventLogger("logs/software_fj.log")
        logger.info("Sistema iniciado")
        logger.error("Algo salió mal", exc)

    El archivo se abre y cierra en cada llamada a `log()`, usando un bloque
    finally para garantizar el cierre aunque ocurra un error inesperado.
    """

    def __init__(self, log_path: str = "logs/software_fj.log") -> None:
        self._log_path = Path(log_path)
        # Crea el directorio de logs si no existe
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"[LOGGER ADVERTENCIA] No se puede crear el directorio de logs: {exc}")

    def log(self, level: LogLevel, message: str, exception: BaseException = None) -> None:
        """
        Escribe una entrada de log con nivel, timestamp y mensaje.

        Si se proporciona una excepción, incluye el traceback completo.
        El archivo siempre se cierra en el bloque finally, incluso si
        ocurre un error durante la escritura.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level.value:<8}] {message}\n"

        # Añade el traceback de la excepción si fue proporcionada
        if exception:
            tb = "".join(traceback.format_exception(
                type(exception), exception, exception.__traceback__))
            for line in tb.splitlines():
                entry += f"    {line}\n"

        # — Uso de finally —
        # El archivo se abre antes del try. El bloque finally garantiza que
        # se cierre correctamente sin importar si la escritura falla.
        archivo = None
        try:
            archivo = open(self._log_path, "a", encoding="utf-8")
            archivo.write(entry)
        except OSError:
            # Si no se puede escribir en el archivo, imprime en consola
            print(entry)
        finally:
            # Siempre se ejecuta: cierra el archivo si fue abierto exitosamente
            if archivo is not None:
                archivo.close()

    # -----------------------------------------------------------------------
    # Métodos de conveniencia por nivel
    # -----------------------------------------------------------------------

    def info(self, msg: str) -> None:
        """Registra un evento informativo normal."""
        self.log(LogLevel.INFO, msg)

    def warning(self, msg: str, exc: BaseException = None) -> None:
        """Registra una advertencia, con excepción opcional."""
        self.log(LogLevel.WARNING, msg, exc)

    def error(self, msg: str, exc: BaseException = None) -> None:
        """Registra un error, con excepción y traceback opcionales."""
        self.log(LogLevel.ERROR, msg, exc)

    def critical(self, msg: str, exc: BaseException = None) -> None:
        """Registra un error crítico que puede comprometer el sistema."""
        self.log(LogLevel.CRITICAL, msg, exc)

    def read_log(self) -> str:
        """
        Lee y retorna el contenido completo del archivo de log.

        Usa finally para garantizar el cierre del archivo incluso
        si ocurre un error durante la lectura.
        """
        archivo = None
        try:
            archivo = open(self._log_path, "r", encoding="utf-8")
            return archivo.read()
        except FileNotFoundError:
            return "(El archivo de log aún no ha sido creado.)"
        except OSError as exc:
            return f"(No se puede leer el log: {exc})"
        finally:
            # Garantiza el cierre aunque read() haya fallado
            if archivo is not None:
                archivo.close()
