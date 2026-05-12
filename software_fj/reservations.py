# =============================================================================
# reservations.py — Módulo de reservas para Software FJ
# =============================================================================
# Define ReservationStatus (Enum) y la clase Reservation que vincula
# un Cliente con un Servicio en una fecha y duración específicas.
# El ciclo de vida de una reserva es: PENDING → CONFIRMED → COMPLETED
#                                       PENDING/CONFIRMED → CANCELLED
# =============================================================================

from datetime import date, datetime
from enum import Enum

from clients import BaseEntity, Client
from services import Service
from exceptions import (
    InvalidParameterError, ReservationError, ReservationCancellationError
)


class ReservationStatus(Enum):
    """Estados posibles de una reserva a lo largo de su ciclo de vida."""
    PENDING   = "PENDING"     # Creada, pendiente de confirmación
    CONFIRMED = "CONFIRMED"   # Confirmada por el sistema o el operador
    COMPLETED = "COMPLETED"   # Servicio completado satisfactoriamente
    CANCELLED = "CANCELLED"   # Cancelada antes de completarse


class Reservation(BaseEntity):
    """
    Vincula un Cliente con un Servicio para una fecha y duración específicas.

    Ciclo de vida:
        PENDING  →  confirm()  →  CONFIRMED
        CONFIRMED → complete() →  COMPLETED
        PENDING/CONFIRMED → cancel() → CANCELLED

    El costo total se calcula dinámicamente mediante calculate_total(),
    delegando en el método calculate_cost() del servicio asociado.

    Parámetros:
        reservation_id   : ID numérico único (asignado por ManagementSystem).
        client           : Instancia de Client ya validada.
        service          : Instancia de Service ya validada.
        reservation_date : Fecha de la reserva (objeto date).
        hours            : Duración en horas (debe estar en rango del servicio).
        notes            : Notas adicionales opcionales.
    """

    def __init__(self, reservation_id: int, client: Client, service: Service,
                 reservation_date: date, hours: float, notes: str = "") -> None:
        super().__init__()
        self._reservation_id   = reservation_id
        self._client           = client
        self._service          = service
        self._reservation_date = reservation_date
        self._hours            = hours
        self._notes            = notes
        self._status           = ReservationStatus.PENDING
        self._confirmed_at     = None   # Fecha/hora de confirmación
        self._completed_at     = None   # Fecha/hora de completación
        self._cancelled_at     = None   # Fecha/hora de cancelación
        self._cancel_reason    = ""     # Motivo de cancelación
        self.validate()

    def validate(self) -> None:
        """
        Valida que el cliente y servicio sean instancias correctas,
        que el servicio esté disponible y que la duración sea válida.
        """
        if not isinstance(self._client, Client):
            raise InvalidParameterError("client", type(self._client).__name__, "debe ser un Client")
        if not isinstance(self._service, Service):
            raise InvalidParameterError("service", type(self._service).__name__, "debe ser un Service")
        # Verifica disponibilidad del servicio (lanza ServiceNotAvailableError si no está disponible)
        self._service.check_availability()
        # Verifica que la duración esté en el rango permitido por el servicio
        self._service._validate_duration(self._hours)

    def describe(self) -> str:
        """Retorna un resumen detallado de la reserva en texto plano."""
        cost = self.calculate_total()
        return (
            f"[Reserva #{self._reservation_id}] Estado: {self._status.value}\n"
            f"  Cliente  : {self._client.full_name}\n"
            f"  Servicio : {self._service.name}\n"
            f"  Fecha    : {self._reservation_date}\n"
            f"  Horas    : {self._hours}h\n"
            f"  Total    : ${cost:,.2f} COP\n"
            f"  Notas    : {self._notes or 'N/A'}"
        )

    # -----------------------------------------------------------------------
    # Transiciones de estado
    # -----------------------------------------------------------------------

    def confirm(self) -> None:
        """
        Confirma la reserva. Solo es válido desde el estado PENDING.
        También re-verifica la disponibilidad del servicio en el momento de confirmar.
        """
        if self._status != ReservationStatus.PENDING:
            raise ReservationError(
                f"No se puede confirmar: el estado es {self._status.value}, se esperaba PENDING.")
        # Segunda verificación de disponibilidad al momento de confirmar
        self._service.check_availability()
        self._status       = ReservationStatus.CONFIRMED
        self._confirmed_at = datetime.now()

    def complete(self) -> None:
        """
        Marca la reserva como completada. Solo es válido desde CONFIRMED.
        Representa que el servicio fue prestado satisfactoriamente.
        """
        if self._status != ReservationStatus.CONFIRMED:
            raise ReservationError(
                f"No se puede completar: el estado es {self._status.value}, se esperaba CONFIRMED.")
        self._status       = ReservationStatus.COMPLETED
        self._completed_at = datetime.now()

    def cancel(self, reason: str = "Sin motivo especificado.") -> None:
        """
        Cancela la reserva con un motivo opcional.
        No se puede cancelar una reserva ya COMPLETED o CANCELLED.
        """
        if self._status in (ReservationStatus.CANCELLED, ReservationStatus.COMPLETED):
            raise ReservationCancellationError(
                f"No se puede cancelar: el estado es {self._status.value}.")
        self._status       = ReservationStatus.CANCELLED
        self._cancelled_at = datetime.now()
        self._cancel_reason = reason

    # -----------------------------------------------------------------------
    # Cálculo de costo
    # -----------------------------------------------------------------------

    def calculate_total(self, tax_rate: float = None, discount_pct: float = 0.0) -> float:
        """
        Calcula el costo total delegando en el servicio asociado.
        Si no se especifica tax_rate, usa el valor por defecto del servicio.
        """
        try:
            if tax_rate is None:
                return self._service.calculate_cost(self._hours, discount_pct=discount_pct)
            return self._service.calculate_cost(self._hours, tax_rate=tax_rate, discount_pct=discount_pct)
        except Exception as exc:
            raise ReservationError(f"El cálculo de costo falló: {exc}") from exc

    # -----------------------------------------------------------------------
    # Propiedades de solo lectura
    # -----------------------------------------------------------------------

    @property
    def reservation_id(self) -> int:
        return self._reservation_id

    @property
    def client(self) -> Client:
        return self._client

    @property
    def service(self) -> Service:
        return self._service

    @property
    def reservation_date(self) -> date:
        return self._reservation_date

    @property
    def hours(self) -> float:
        return self._hours

    @property
    def status(self) -> ReservationStatus:
        return self._status

    @property
    def notes(self) -> str:
        return self._notes
