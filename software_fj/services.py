# =============================================================================
# services.py — Módulo de servicios para Software FJ
# =============================================================================
# Define la jerarquía de clases de servicios:
#   Service (ABC)
#   ├── RoomReservationService      — Salas de reunión (1-8 h)
#   ├── EquipmentRentalService      — Alquiler de equipos (2-24 h)
#   └── SpecializedConsultingService — Consultoría especializada (0.5-4 h)
# =============================================================================

from abc import abstractmethod
from typing import List

from clients import BaseEntity
from exceptions import (
    ServiceValidationError, ServiceNotAvailableError,
    InvalidDurationError, InvalidCostError
)

# Tasa de IVA por defecto (19 %) y descuento máximo permitido (50 %)
_DEFAULT_TAX  = 0.19
_MAX_DISCOUNT = 50.0


# =============================================================================
# SERVICIO BASE (abstracto)
# =============================================================================

class Service(BaseEntity):
    """
    Clase base abstracta para todos los servicios de Software FJ.

    Cada subclase debe definir:
        - min_hours / max_hours : rango válido de duración.
        - validate()            : validaciones específicas del tipo de servicio.
        - calculate_cost()      : cálculo del costo total según horas y parámetros.
        - describe()            : descripción legible del servicio.

    Los métodos _validate_base() y _apply_tax_discount() son utilidades
    compartidas disponibles para todas las subclases.
    """

    def __init__(self, name: str, base_cost_per_hour: float, available: bool = True) -> None:
        super().__init__()
        self._name               = name
        self._base_cost_per_hour = base_cost_per_hour
        self._available          = available
        self.validate()

    # -----------------------------------------------------------------------
    # Métodos de utilidad protegidos (para uso interno en subclases)
    # -----------------------------------------------------------------------

    def _validate_base(self) -> None:
        """Valida que el nombre y el costo base sean válidos."""
        if not isinstance(self._name, str) or not self._name.strip():
            raise ServiceValidationError("El nombre del servicio no puede estar vacío.")
        if not isinstance(self._base_cost_per_hour, (int, float)) or self._base_cost_per_hour <= 0:
            raise ServiceValidationError("base_cost_per_hour debe ser mayor que cero.")

    def _validate_duration(self, hours: float) -> None:
        """
        Verifica que la duración esté dentro del rango permitido por el servicio.
        Lanza InvalidDurationError si está fuera de rango.
        """
        if not isinstance(hours, (int, float)) or not (self.min_hours <= hours <= self.max_hours):
            raise InvalidDurationError(hours, self.min_hours, self.max_hours)

    def _apply_tax_discount(self, base: float, tax: float, disc: float) -> float:
        """
        Aplica impuesto y descuento al costo base.

        Fórmula: base × (1 - descuento/100) × (1 + impuesto)
        Retorna el valor redondeado a 2 decimales.
        """
        if not (0 <= tax <= 1):
            raise InvalidCostError(f"tax_rate debe estar entre 0 y 1, recibido: {tax}.")
        if not (0 <= disc <= _MAX_DISCOUNT):
            raise InvalidCostError(f"discount_pct debe estar entre 0 y {_MAX_DISCOUNT}, recibido: {disc}.")
        return round(base * (1 - disc / 100) * (1 + tax), 2)

    def check_availability(self) -> None:
        """Lanza ServiceNotAvailableError si el servicio no está disponible."""
        if not self._available:
            raise ServiceNotAvailableError(self._name)

    # -----------------------------------------------------------------------
    # Métodos abstractos que deben implementar las subclases
    # -----------------------------------------------------------------------

    @abstractmethod
    def calculate_cost(self, hours: float, tax_rate: float = _DEFAULT_TAX,
                       discount_pct: float = 0.0) -> float:
        """Calcula el costo total para una reserva con los parámetros dados."""

    @property
    @abstractmethod
    def min_hours(self) -> float:
        """Duración mínima permitida (en horas)."""

    @property
    @abstractmethod
    def max_hours(self) -> float:
        """Duración máxima permitida (en horas)."""

    # -----------------------------------------------------------------------
    # Propiedades comunes a todos los servicios
    # -----------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def base_cost_per_hour(self) -> float:
        return self._base_cost_per_hour

    @property
    def available(self) -> bool:
        return self._available

    @available.setter
    def available(self, value: bool) -> None:
        """Permite habilitar o deshabilitar el servicio."""
        self._available = value

    @property
    def service_type(self) -> str:
        """Retorna el nombre de la clase del servicio (p.ej. 'RoomReservationService')."""
        return self.__class__.__name__


# =============================================================================
# SERVICIO: RESERVA DE SALA
# =============================================================================

class RoomReservationService(Service):
    """
    Servicio para reservar salas de reunión o conferencia.
    Duración permitida: 1 a 8 horas.

    El costo se calcula como: costo_base_por_hora × horas (+ impuesto - descuento).
    """

    def __init__(self, name: str, base_cost_per_hour: float,
                 room_name: str, capacity: int, available: bool = True) -> None:
        # Se asignan antes de llamar a super() porque validate() los necesita
        self._room_name = room_name
        self._capacity  = capacity
        super().__init__(name, base_cost_per_hour, available)

    def validate(self) -> None:
        """Valida campos base más nombre de sala y capacidad."""
        self._validate_base()
        if not isinstance(self._room_name, str) or not self._room_name.strip():
            raise ServiceValidationError("room_name debe ser una cadena no vacía.")
        if not isinstance(self._capacity, int) or self._capacity < 1:
            raise ServiceValidationError("capacity debe ser un entero >= 1.")

    def calculate_cost(self, hours: float, tax_rate: float = _DEFAULT_TAX,
                       discount_pct: float = 0.0) -> float:
        """Costo = tarifa_por_hora × horas, con impuesto y descuento aplicados."""
        self._validate_duration(hours)
        return self._apply_tax_discount(self._base_cost_per_hour * hours, tax_rate, discount_pct)

    def describe(self) -> str:
        status = "Disponible" if self._available else "No disponible"
        return (f"[Sala] {self._name} | Sala: {self._room_name} | "
                f"Capacidad: {self._capacity} | Tarifa: ${self._base_cost_per_hour:,.0f}/h | {status}")

    @property
    def min_hours(self) -> float:
        return 1.0

    @property
    def max_hours(self) -> float:
        return 8.0

    @property
    def room_name(self) -> str:
        return self._room_name

    @property
    def capacity(self) -> int:
        return self._capacity


# =============================================================================
# SERVICIO: ALQUILER DE EQUIPOS
# =============================================================================

class EquipmentRentalService(Service):
    """
    Servicio para alquiler de paquetes de equipos tecnológicos.
    Duración permitida: 2 a 24 horas.

    El costo se calcula como: costo_base × cantidad_de_items × horas.
    Así, paquetes más grandes tienen un costo proporcionalmente mayor.
    """

    def __init__(self, name: str, base_cost_per_hour: float,
                 equipment_list: List[str], available: bool = True) -> None:
        self._equipment_list = equipment_list
        super().__init__(name, base_cost_per_hour, available)

    def validate(self) -> None:
        """Valida campos base más la lista de equipos (debe tener al menos 1 item)."""
        self._validate_base()
        if not isinstance(self._equipment_list, list) or len(self._equipment_list) == 0:
            raise ServiceValidationError("equipment_list debe contener al menos un ítem.")

    def calculate_cost(self, hours: float, tax_rate: float = _DEFAULT_TAX,
                       discount_pct: float = 0.0) -> float:
        """Costo = tarifa_por_item × número_de_items × horas, con impuesto y descuento."""
        self._validate_duration(hours)
        return self._apply_tax_discount(
            self._base_cost_per_hour * len(self._equipment_list) * hours,
            tax_rate, discount_pct
        )

    def describe(self) -> str:
        status = "Disponible" if self._available else "No disponible"
        items  = ", ".join(self._equipment_list)
        return (f"[Equipo] {self._name} | Ítems: {items} | "
                f"Tarifa: ${self._base_cost_per_hour:,.0f}/ítem/h | {status}")

    @property
    def min_hours(self) -> float:
        return 2.0

    @property
    def max_hours(self) -> float:
        return 24.0

    @property
    def equipment_list(self) -> List[str]:
        """Retorna una copia de la lista para evitar mutaciones externas."""
        return list(self._equipment_list)


# =============================================================================
# SERVICIO: CONSULTORÍA ESPECIALIZADA
# =============================================================================

class SpecializedConsultingService(Service):
    """
    Servicio para sesiones de consultoría profesional.
    Duración permitida: 0.5 a 4 horas.

    El costo incluye un multiplicador según la seniority del experto:
        junior → ×1.0  |  mid → ×1.3  |  senior → ×1.6  |  lead → ×2.0
    """

    # Tabla de multiplicadores por nivel de experiencia
    _SENIORITY = {"junior": 1.0, "mid": 1.3, "senior": 1.6, "lead": 2.0}

    def __init__(self, name: str, base_cost_per_hour: float, specialty: str,
                 expert_name: str, seniority: str = "mid", available: bool = True) -> None:
        self._specialty   = specialty
        self._expert_name = expert_name
        self._seniority   = seniority.lower().strip()
        super().__init__(name, base_cost_per_hour, available)

    def validate(self) -> None:
        """Valida campos base más especialidad, nombre del experto y nivel de seniority."""
        self._validate_base()
        if not self._specialty.strip():
            raise ServiceValidationError("specialty no puede estar vacío.")
        if not self._expert_name.strip():
            raise ServiceValidationError("expert_name no puede estar vacío.")
        if self._seniority not in self._SENIORITY:
            raise ServiceValidationError(
                f"seniority debe ser uno de {list(self._SENIORITY.keys())}.")

    def calculate_cost(self, hours: float, tax_rate: float = _DEFAULT_TAX,
                       discount_pct: float = 0.0) -> float:
        """Costo = tarifa_base × multiplicador_seniority × horas, con impuesto y descuento."""
        self._validate_duration(hours)
        return self._apply_tax_discount(
            self._base_cost_per_hour * self._SENIORITY[self._seniority] * hours,
            tax_rate, discount_pct
        )

    def describe(self) -> str:
        status = "Disponible" if self._available else "No disponible"
        mult   = self._SENIORITY[self._seniority]
        return (f"[Consultoría] {self._name} | {self._specialty} | "
                f"Experto: {self._expert_name} ({self._seniority.capitalize()}, ×{mult}) | "
                f"Tarifa: ${self._base_cost_per_hour:,.0f}/h | {status}")

    @property
    def min_hours(self) -> float:
        return 0.5

    @property
    def max_hours(self) -> float:
        return 4.0

    @property
    def specialty(self) -> str:
        return self._specialty

    @property
    def expert_name(self) -> str:
        return self._expert_name

    @property
    def seniority(self) -> str:
        return self._seniority
