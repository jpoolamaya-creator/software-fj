# =============================================================================
# exceptions.py — Excepciones personalizadas del sistema Software FJ
# =============================================================================
# Todas las excepciones heredan de SoftwareFJBaseError para facilitar
# el manejo centralizado de errores en el resto del sistema.
# =============================================================================


class SoftwareFJBaseError(Exception):
    """
    Excepción raíz del sistema Software FJ.
    Todas las demás excepciones del dominio heredan de esta clase,
    lo que permite capturarlas con un único bloque except cuando sea necesario.
    """

    def __init__(self, message: str, details: str = "") -> None:
        self.message = message
        self.details = details
        # Construye el mensaje completo con detalles opcionales
        full = message if not details else f"{message} | Detalles: {details}"
        super().__init__(full)


# ---------------------------------------------------------------------------
# Excepciones de Cliente
# ---------------------------------------------------------------------------

class ClientValidationError(SoftwareFJBaseError):
    """Se lanza cuando los datos de registro de un cliente no pasan la validación."""


class DuplicateClientError(SoftwareFJBaseError):
    """Se lanza cuando se intenta registrar un ID de cliente que ya existe."""

    def __init__(self, client_id: int) -> None:
        super().__init__(
            f"El cliente con ID '{client_id}' ya está registrado.",
            f"client_id={client_id}"
        )


# ---------------------------------------------------------------------------
# Excepciones de Servicio
# ---------------------------------------------------------------------------

class ServiceValidationError(SoftwareFJBaseError):
    """Se lanza cuando un servicio tiene parámetros inválidos al ser creado."""


class ServiceNotAvailableError(SoftwareFJBaseError):
    """Se lanza cuando se intenta reservar un servicio que no está disponible."""

    def __init__(self, service_name: str) -> None:
        super().__init__(
            f"El servicio '{service_name}' no está disponible actualmente.",
            f"service='{service_name}'"
        )


# ---------------------------------------------------------------------------
# Excepciones de Reserva
# ---------------------------------------------------------------------------

class ReservationError(SoftwareFJBaseError):
    """Error general de reserva. Base para errores más específicos."""


class ReservationConflictError(ReservationError):
    """Se lanza cuando se detecta una reserva duplicada para el mismo cliente, servicio y fecha."""

    def __init__(self, client_id: int, service_name: str, date_str: str) -> None:
        super().__init__(
            f"El cliente {client_id} ya tiene una reserva para '{service_name}' el {date_str}.",
            f"client_id={client_id}, service='{service_name}', date={date_str}"
        )


class ReservationCancellationError(ReservationError):
    """Se lanza cuando una cancelación no está permitida (p.ej. reserva ya completada)."""


# ---------------------------------------------------------------------------
# Excepciones de Validación General
# ---------------------------------------------------------------------------

class InvalidDurationError(SoftwareFJBaseError):
    """Se lanza cuando la duración solicitada está fuera del rango permitido por el servicio."""

    def __init__(self, duration: float, min_h: float, max_h: float) -> None:
        super().__init__(
            f"La duración {duration}h está fuera del rango válido [{min_h}h - {max_h}h].",
            f"duration={duration}, min={min_h}, max={max_h}"
        )


class InvalidCostError(SoftwareFJBaseError):
    """Se lanza cuando los valores de costo, descuento o impuesto son inválidos."""


class InvalidParameterError(SoftwareFJBaseError):
    """Se lanza cuando el valor de un parámetro es inaceptable en cualquier operación."""

    def __init__(self, param: str, value: object, reason: str = "") -> None:
        msg = f"Valor inválido para '{param}': {value!r}."
        if reason:
            msg += f" Razón: {reason}"
        super().__init__(msg, f"param='{param}', value={value!r}")
