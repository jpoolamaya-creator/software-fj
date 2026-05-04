# =============================================================================
# Software FJ - Integrated Management System with Tkinter GUI
# =============================================================================
# Estudiante: Jean Pool Muñoz Amaya
# Tutor: Juan Pablo Zambrano Sanjuan
# Grupo: 371
# Programa Académico: Ingeniería de Sistemas
# Código Fuente: Autoría Propia
# Purpose : Complete GUI application for managing clients, services and
#           reservations using Python's built-in Tkinter library.
#           ALL code is in a single file so there are NO import errors.
# =============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import re
import uuid
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Optional
from pathlib import Path
import traceback


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class SoftwareFJBaseError(Exception):
    """Root exception for every error raised inside the Software FJ system."""
    def __init__(self, message: str, details: str = "") -> None:
        self.message = message
        self.details = details
        full = message if not details else f"{message} | Details: {details}"
        super().__init__(full)


class ClientValidationError(SoftwareFJBaseError):
    """Raised when client registration data fails validation."""


class DuplicateClientError(SoftwareFJBaseError):
    """Raised when a client ID already exists."""
    def __init__(self, client_id: int) -> None:
        super().__init__(f"Client ID '{client_id}' already exists.", f"client_id={client_id}")


class ServiceValidationError(SoftwareFJBaseError):
    """Raised when a service has invalid parameters."""


class ServiceNotAvailableError(SoftwareFJBaseError):
    """Raised when trying to reserve an unavailable service."""
    def __init__(self, service_name: str) -> None:
        super().__init__(f"Service '{service_name}' is not available.", f"service='{service_name}'")


class ReservationError(SoftwareFJBaseError):
    """General reservation error."""


class ReservationConflictError(ReservationError):
    """Raised when a duplicate reservation is detected."""
    def __init__(self, client_id: int, service_name: str, date_str: str) -> None:
        super().__init__(
            f"Client {client_id} already has a reservation for '{service_name}' on {date_str}.",
            f"client_id={client_id}, service='{service_name}', date={date_str}"
        )


class ReservationCancellationError(ReservationError):
    """Raised when a cancellation is not allowed."""


class InvalidDurationError(SoftwareFJBaseError):
    """Raised when duration is outside allowed range."""
    def __init__(self, duration: float, min_h: float, max_h: float) -> None:
        super().__init__(
            f"Duration {duration}h is outside valid range [{min_h}h - {max_h}h].",
            f"duration={duration}, min={min_h}, max={max_h}"
        )


class InvalidCostError(SoftwareFJBaseError):
    """Raised when cost/discount/tax values are invalid."""


class InvalidParameterError(SoftwareFJBaseError):
    """Raised when a parameter value is unacceptable."""
    def __init__(self, param: str, value: object, reason: str = "") -> None:
        msg = f"Invalid value for '{param}': {value!r}."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg, f"param='{param}', value={value!r}")


# =============================================================================
# LOGGER
# =============================================================================

class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventLogger:
    """Writes timestamped log entries to a plain-text file."""

    def __init__(self, log_path: str = "logs/software_fj.log") -> None:
        self._log_path = Path(log_path)
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"[LOGGER WARNING] Cannot create log dir: {exc}")

    def log(self, level: LogLevel, message: str, exception: BaseException = None) -> None:
        """Write a single timestamped log entry."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level.value:<8}] {message}\n"
        if exception:
            tb = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            for line in tb.splitlines():
                entry += f"    {line}\n"
        try:
            with open(self._log_path, "a", encoding="utf-8") as fh:
                fh.write(entry)
        except OSError:
            print(entry)

    def info(self, msg: str) -> None:
        self.log(LogLevel.INFO, msg)

    def warning(self, msg: str, exc: BaseException = None) -> None:
        self.log(LogLevel.WARNING, msg, exc)

    def error(self, msg: str, exc: BaseException = None) -> None:
        self.log(LogLevel.ERROR, msg, exc)

    def read_log(self) -> str:
        try:
            return self._log_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return "(Log file not yet created.)"
        except OSError as exc:
            return f"(Cannot read log: {exc})"


# =============================================================================
# BASE ENTITY
# =============================================================================

class BaseEntity(ABC):
    """Abstract root class for all domain entities."""

    def __init__(self) -> None:
        self._entity_id = str(uuid.uuid4())
        self._created_at = datetime.now()

    @abstractmethod
    def validate(self) -> None:
        """Validate internal state. Raises on failure."""

    @abstractmethod
    def describe(self) -> str:
        """Return a human-readable description."""

    def __str__(self) -> str:
        return self.describe()


# =============================================================================
# CLIENT
# =============================================================================

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_RE = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")


class Client(BaseEntity):
    """Represents a registered client with strict field validation."""

    def __init__(self, client_id: int, first_name: str, last_name: str,
                 email: str, phone: str) -> None:
        super().__init__()
        self._client_id = client_id
        self._first_name = first_name
        self._last_name = last_name
        self._email = email
        self._phone = phone
        self.validate()

    def validate(self) -> None:
        """Validate all client fields."""
        # client_id
        if not isinstance(self._client_id, int) or isinstance(self._client_id, bool):
            raise ClientValidationError("client_id must be an integer.")
        if self._client_id <= 0:
            raise ClientValidationError("client_id must be > 0.")
        # names
        for field, value in [("first_name", self._first_name), ("last_name", self._last_name)]:
            if not isinstance(value, str) or not value.strip():
                raise ClientValidationError(f"{field} cannot be empty.")
            if len(value.strip()) < 2:
                raise ClientValidationError(f"{field} is too short (min 2 chars).")
            if not any(c.isalpha() for c in value):
                raise ClientValidationError(f"{field} must contain at least one letter.")
        # email
        if not _EMAIL_RE.match(self._email.strip()):
            raise ClientValidationError(f"'{self._email}' is not a valid email address.")
        # phone
        if not _PHONE_RE.match(self._phone.strip()):
            raise ClientValidationError(f"'{self._phone}' is not a valid phone number.")

    def describe(self) -> str:
        return f"[#{self._client_id}] {self._first_name} {self._last_name} | {self._email} | {self._phone}"

    @property
    def client_id(self) -> int:
        return self._client_id

    @property
    def full_name(self) -> str:
        return f"{self._first_name} {self._last_name}"

    @property
    def email(self) -> str:
        return self._email

    @property
    def phone(self) -> str:
        return self._phone


# =============================================================================
# SERVICES
# =============================================================================

_DEFAULT_TAX = 0.19
_MAX_DISCOUNT = 50.0


class Service(BaseEntity, ABC):
    """Abstract base for all Software FJ services."""

    def __init__(self, name: str, base_cost_per_hour: float, available: bool = True) -> None:
        super().__init__()
        self._name = name
        self._base_cost_per_hour = base_cost_per_hour
        self._available = available
        self.validate()

    def _validate_base(self) -> None:
        if not isinstance(self._name, str) or not self._name.strip():
            raise ServiceValidationError("Service name must be a non-empty string.")
        if not isinstance(self._base_cost_per_hour, (int, float)) or self._base_cost_per_hour <= 0:
            raise ServiceValidationError("base_cost_per_hour must be greater than zero.")

    def _validate_duration(self, hours: float) -> None:
        if not isinstance(hours, (int, float)) or not (self.min_hours <= hours <= self.max_hours):
            raise InvalidDurationError(hours, self.min_hours, self.max_hours)

    def _apply_tax_discount(self, base: float, tax: float, disc: float) -> float:
        if not (0 <= tax <= 1):
            raise InvalidCostError(f"tax_rate must be 0-1, got {tax}.")
        if not (0 <= disc <= _MAX_DISCOUNT):
            raise InvalidCostError(f"discount_pct must be 0-{_MAX_DISCOUNT}, got {disc}.")
        return round(base * (1 - disc / 100) * (1 + tax), 2)

    def check_availability(self) -> None:
        if not self._available:
            raise ServiceNotAvailableError(self._name)

    @abstractmethod
    def calculate_cost(self, hours: float, tax_rate: float = _DEFAULT_TAX, discount_pct: float = 0.0) -> float:
        """Calculate total cost for a booking."""

    @property
    @abstractmethod
    def min_hours(self) -> float:
        pass

    @property
    @abstractmethod
    def max_hours(self) -> float:
        pass

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
        self._available = value

    @property
    def service_type(self) -> str:
        return self.__class__.__name__


class RoomReservationService(Service):
    """Service for reserving conference/meeting rooms. Duration: 1-8 hours."""

    def __init__(self, name: str, base_cost_per_hour: float,
                 room_name: str, capacity: int, available: bool = True) -> None:
        self._room_name = room_name
        self._capacity = capacity
        super().__init__(name, base_cost_per_hour, available)

    def validate(self) -> None:
        self._validate_base()
        if not isinstance(self._room_name, str) or not self._room_name.strip():
            raise ServiceValidationError("room_name must be a non-empty string.")
        if not isinstance(self._capacity, int) or self._capacity < 1:
            raise ServiceValidationError("capacity must be an integer >= 1.")

    def calculate_cost(self, hours: float, tax_rate: float = _DEFAULT_TAX, discount_pct: float = 0.0) -> float:
        self._validate_duration(hours)
        return self._apply_tax_discount(self._base_cost_per_hour * hours, tax_rate, discount_pct)

    def describe(self) -> str:
        status = "Available" if self._available else "Unavailable"
        return (f"[Room] {self._name} | Room: {self._room_name} | "
                f"Capacity: {self._capacity} | Rate: ${self._base_cost_per_hour:,.0f}/h | {status}")

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


class EquipmentRentalService(Service):
    """Service for renting equipment packages. Duration: 2-24 hours."""

    def __init__(self, name: str, base_cost_per_hour: float,
                 equipment_list: List[str], available: bool = True) -> None:
        self._equipment_list = equipment_list
        super().__init__(name, base_cost_per_hour, available)

    def validate(self) -> None:
        self._validate_base()
        if not isinstance(self._equipment_list, list) or len(self._equipment_list) == 0:
            raise ServiceValidationError("equipment_list must contain at least one item.")

    def calculate_cost(self, hours: float, tax_rate: float = _DEFAULT_TAX, discount_pct: float = 0.0) -> float:
        self._validate_duration(hours)
        return self._apply_tax_discount(
            self._base_cost_per_hour * len(self._equipment_list) * hours, tax_rate, discount_pct)

    def describe(self) -> str:
        status = "Available" if self._available else "Unavailable"
        items = ", ".join(self._equipment_list)
        return f"[Equipment] {self._name} | Items: {items} | Rate: ${self._base_cost_per_hour:,.0f}/item/h | {status}"

    @property
    def min_hours(self) -> float:
        return 2.0

    @property
    def max_hours(self) -> float:
        return 24.0

    @property
    def equipment_list(self) -> List[str]:
        return list(self._equipment_list)


class SpecializedConsultingService(Service):
    """Service for professional consulting sessions. Duration: 0.5-4 hours."""

    _SENIORITY = {"junior": 1.0, "mid": 1.3, "senior": 1.6, "lead": 2.0}

    def __init__(self, name: str, base_cost_per_hour: float, specialty: str,
                 expert_name: str, seniority: str = "mid", available: bool = True) -> None:
        self._specialty = specialty
        self._expert_name = expert_name
        self._seniority = seniority.lower().strip()
        super().__init__(name, base_cost_per_hour, available)

    def validate(self) -> None:
        self._validate_base()
        if not self._specialty.strip():
            raise ServiceValidationError("specialty cannot be empty.")
        if not self._expert_name.strip():
            raise ServiceValidationError("expert_name cannot be empty.")
        if self._seniority not in self._SENIORITY:
            raise ServiceValidationError(f"seniority must be one of {list(self._SENIORITY.keys())}.")

    def calculate_cost(self, hours: float, tax_rate: float = _DEFAULT_TAX, discount_pct: float = 0.0) -> float:
        self._validate_duration(hours)
        return self._apply_tax_discount(
            self._base_cost_per_hour * self._SENIORITY[self._seniority] * hours, tax_rate, discount_pct)

    def describe(self) -> str:
        status = "Available" if self._available else "Unavailable"
        mult = self._SENIORITY[self._seniority]
        return (f"[Consulting] {self._name} | {self._specialty} | "
                f"Expert: {self._expert_name} ({self._seniority.capitalize()}, x{mult}) | "
                f"Rate: ${self._base_cost_per_hour:,.0f}/h | {status}")

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


# =============================================================================
# RESERVATION
# =============================================================================

class ReservationStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Reservation(BaseEntity):
    """Links a Client to a Service for a specific date and duration."""

    def __init__(self, reservation_id: int, client: Client, service: Service,
                 reservation_date: date, hours: float, notes: str = "") -> None:
        super().__init__()
        self._reservation_id = reservation_id
        self._client = client
        self._service = service
        self._reservation_date = reservation_date
        self._hours = hours
        self._notes = notes
        self._status = ReservationStatus.PENDING
        self._confirmed_at = None
        self._completed_at = None
        self._cancelled_at = None
        self.validate()

    def validate(self) -> None:
        if not isinstance(self._client, Client):
            raise InvalidParameterError("client", type(self._client).__name__, "must be a Client")
        if not isinstance(self._service, Service):
            raise InvalidParameterError("service", type(self._service).__name__, "must be a Service")
        self._service.check_availability()
        self._service._validate_duration(self._hours)

    def describe(self) -> str:
        cost = self.calculate_total()
        return (f"[Reservation #{self._reservation_id}] Status: {self._status.value}\n"
                f"  Client : {self._client.full_name}\n"
                f"  Service: {self._service.name}\n"
                f"  Date   : {self._reservation_date}\n"
                f"  Hours  : {self._hours}h\n"
                f"  Total  : ${cost:,.2f} COP\n"
                f"  Notes  : {self._notes or 'N/A'}")

    def confirm(self) -> None:
        if self._status != ReservationStatus.PENDING:
            raise ReservationError(f"Cannot confirm: status is {self._status.value}, expected PENDING.")
        self._service.check_availability()
        self._status = ReservationStatus.CONFIRMED
        self._confirmed_at = datetime.now()

    def complete(self) -> None:
        if self._status != ReservationStatus.CONFIRMED:
            raise ReservationError(f"Cannot complete: status is {self._status.value}, expected CONFIRMED.")
        self._status = ReservationStatus.COMPLETED
        self._completed_at = datetime.now()

    def cancel(self, reason: str = "No reason.") -> None:
        if self._status in (ReservationStatus.CANCELLED, ReservationStatus.COMPLETED):
            raise ReservationCancellationError(f"Cannot cancel: status is {self._status.value}.")
        self._status = ReservationStatus.CANCELLED
        self._cancelled_at = datetime.now()
        self._cancel_reason = reason

    def calculate_total(self, tax_rate: float = None, discount_pct: float = 0.0) -> float:
        try:
            if tax_rate is None:
                return self._service.calculate_cost(self._hours, discount_pct=discount_pct)
            return self._service.calculate_cost(self._hours, tax_rate=tax_rate, discount_pct=discount_pct)
        except Exception as exc:
            raise ReservationError(f"Cost calculation failed: {exc}") from exc

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


# =============================================================================
# MANAGEMENT SYSTEM (business logic, no GUI)
# =============================================================================

class ManagementSystem:
    """Central orchestrator. All errors caught internally."""

    def __init__(self) -> None:
        self._clients: Dict[int, Client] = {}
        self._services: Dict[str, Service] = {}
        self._reservations: Dict[int, Reservation] = {}
        self._logger = EventLogger("logs/software_fj.log")
        self._next_res_id = 1
        self._logger.info("Software FJ started.")

    # --- Clients -----------------------------------------------------------

    def register_client(self, client_id: int, first_name: str, last_name: str,
                        email: str, phone: str):
        """Register a new client. Returns (client, error_message)."""
        try:
            if client_id in self._clients:
                raise DuplicateClientError(client_id)
            client = Client(client_id, first_name, last_name, email, phone)
            self._clients[client_id] = client
            self._logger.info(f"CLIENT REGISTERED: {client.describe()}")
            return client, None
        except SoftwareFJBaseError as exc:
            self._logger.error(f"CLIENT ERROR: {exc}", exc)
            return None, str(exc)
        except Exception as exc:
            self._logger.error(f"UNEXPECTED CLIENT ERROR: {exc}", exc)
            return None, str(exc)

    def list_clients(self) -> List[Client]:
        return sorted(self._clients.values(), key=lambda c: c.client_id)

    def delete_client(self, client_id: int):
        """Delete a client. Returns (True, None) or (False, error)."""
        try:
            if client_id not in self._clients:
                raise InvalidParameterError("client_id", client_id, "not found")
            # Check no active reservations
            for res in self._reservations.values():
                if res.client.client_id == client_id and res.status in (
                        ReservationStatus.PENDING, ReservationStatus.CONFIRMED):
                    raise ReservationError(
                        f"Cannot delete client #{client_id}: has active reservations.")
            del self._clients[client_id]
            self._logger.info(f"CLIENT DELETED: id={client_id}")
            return True, None
        except SoftwareFJBaseError as exc:
            self._logger.error(f"DELETE CLIENT ERROR: {exc}", exc)
            return False, str(exc)

    # --- Services ----------------------------------------------------------

    def add_service(self, service: Service):
        """Add a service. Returns (service, error_message)."""
        try:
            if service.name in self._services:
                raise SoftwareFJBaseError(f"Service '{service.name}' already exists.")
            self._services[service.name] = service
            self._logger.info(f"SERVICE ADDED: {service.describe()}")
            return service, None
        except SoftwareFJBaseError as exc:
            self._logger.error(f"SERVICE ERROR: {exc}", exc)
            return None, str(exc)
        except Exception as exc:
            self._logger.error(f"UNEXPECTED SERVICE ERROR: {exc}", exc)
            return None, str(exc)

    def list_services(self) -> List[Service]:
        return sorted(self._services.values(), key=lambda s: s.name)

    def toggle_service(self, name: str):
        """Toggle service availability."""
        try:
            svc = self._services.get(name)
            if not svc:
                raise InvalidParameterError("name", name, "service not found")
            svc.available = not svc.available
            status = "enabled" if svc.available else "disabled"
            self._logger.info(f"SERVICE {status.upper()}: '{name}'")
            return True, f"Service '{name}' is now {status}."
        except SoftwareFJBaseError as exc:
            return False, str(exc)

    # --- Reservations ------------------------------------------------------

    def create_reservation(self, client_id: int, service_name: str,
                           reservation_date: date, hours: float, notes: str = ""):
        """Create a reservation. Returns (reservation, error_message)."""
        try:
            client = self._clients.get(client_id)
            if not client:
                raise InvalidParameterError("client_id", client_id, "client not found")
            service = self._services.get(service_name)
            if not service:
                raise InvalidParameterError("service_name", service_name, "service not found")
            # Conflict check
            for res in self._reservations.values():
                if (res.client.client_id == client_id and
                        res.service.name == service_name and
                        res.reservation_date == reservation_date and
                        res.status in (ReservationStatus.PENDING, ReservationStatus.CONFIRMED)):
                    raise ReservationConflictError(client_id, service_name, str(reservation_date))
            reservation = Reservation(
                self._next_res_id, client, service, reservation_date, hours, notes)
            self._reservations[self._next_res_id] = reservation
            self._next_res_id += 1
            cost = reservation.calculate_total()
            self._logger.info(
                f"RESERVATION CREATED: #{reservation.reservation_id} | "
                f"Client #{client_id} | '{service_name}' | {reservation_date} | {hours}h | ${cost:,.2f}")
            return reservation, None
        except SoftwareFJBaseError as exc:
            self._logger.error(f"RESERVATION ERROR: {exc}", exc)
            return None, str(exc)
        except Exception as exc:
            self._logger.error(f"UNEXPECTED RESERVATION ERROR: {exc}", exc)
            return None, str(exc)

    def confirm_reservation(self, res_id: int):
        try:
            res = self._reservations.get(res_id)
            if not res:
                raise InvalidParameterError("reservation_id", res_id, "not found")
            res.confirm()
            self._logger.info(f"RESERVATION CONFIRMED: #{res_id}")
            return True, f"Reservation #{res_id} confirmed."
        except SoftwareFJBaseError as exc:
            self._logger.error(f"CONFIRM ERROR: {exc}", exc)
            return False, str(exc)

    def complete_reservation(self, res_id: int):
        try:
            res = self._reservations.get(res_id)
            if not res:
                raise InvalidParameterError("reservation_id", res_id, "not found")
            res.complete()
            self._logger.info(f"RESERVATION COMPLETED: #{res_id}")
            return True, f"Reservation #{res_id} completed."
        except SoftwareFJBaseError as exc:
            self._logger.error(f"COMPLETE ERROR: {exc}", exc)
            return False, str(exc)

    def cancel_reservation(self, res_id: int, reason: str = "Cancelled by user."):
        try:
            res = self._reservations.get(res_id)
            if not res:
                raise InvalidParameterError("reservation_id", res_id, "not found")
            res.cancel(reason)
            self._logger.info(f"RESERVATION CANCELLED: #{res_id}")
            return True, f"Reservation #{res_id} cancelled."
        except SoftwareFJBaseError as exc:
            self._logger.error(f"CANCEL ERROR: {exc}", exc)
            return False, str(exc)

    def list_reservations(self, status_filter: ReservationStatus = None) -> List[Reservation]:
        result = sorted(self._reservations.values(), key=lambda r: r.reservation_id)
        if status_filter:
            result = [r for r in result if r.status == status_filter]
        return result

    def get_log(self) -> str:
        return self._logger.read_log()

    def get_stats(self) -> dict:
        total = len(self._reservations)
        by_status = {s: 0 for s in ReservationStatus}
        for r in self._reservations.values():
            by_status[r.status] += 1
        return {
            "clients": len(self._clients),
            "services": len(self._services),
            "reservations": total,
            "pending": by_status[ReservationStatus.PENDING],
            "confirmed": by_status[ReservationStatus.CONFIRMED],
            "completed": by_status[ReservationStatus.COMPLETED],
            "cancelled": by_status[ReservationStatus.CANCELLED],
        }


# =============================================================================
# GUI APPLICATION
# =============================================================================

# Color palette
COLORS = {
    "bg":         "#1E1E2E",   # dark background
    "sidebar":    "#181825",   # sidebar
    "card":       "#313244",   # card/frame bg
    "accent":     "#CBA6F7",   # purple accent
    "accent2":    "#89B4FA",   # blue
    "green":      "#A6E3A1",   # success
    "red":        "#F38BA8",   # error
    "yellow":     "#F9E2AF",   # warning
    "text":       "#CDD6F4",   # main text
    "subtext":    "#BAC2DE",   # secondary text
    "border":     "#45475A",   # borders
    "pending":    "#F9E2AF",
    "confirmed":  "#89B4FA",
    "completed":  "#A6E3A1",
    "cancelled":  "#F38BA8",
}

FONTS = {
    "title":   ("Segoe UI", 18, "bold"),
    "heading": ("Segoe UI", 13, "bold"),
    "body":    ("Segoe UI", 11),
    "small":   ("Segoe UI", 10),
    "mono":    ("Consolas", 10),
    "btn":     ("Segoe UI", 11, "bold"),
}


class SoftwareFJApp(tk.Tk):
    """Main application window for Software FJ."""

    def __init__(self) -> None:
        super().__init__()
        self.system = ManagementSystem()
        self.title("Software FJ – Integrated Management System")
        self.geometry("1200x750")
        self.minsize(1000, 650)
        self.configure(bg=COLORS["bg"])
        self._build_ui()
        self._load_demo_data()
        self._show_frame("dashboard")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Build the sidebar + main content area."""
        # ---- Sidebar --------------------------------------------------
        self.sidebar = tk.Frame(self, bg=COLORS["sidebar"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        tk.Label(self.sidebar, text="Software FJ",
                 bg=COLORS["sidebar"], fg=COLORS["accent"],
                 font=("Segoe UI", 16, "bold")).pack(pady=(24, 4))
        tk.Label(self.sidebar, text="UNAD · 213023",
                 bg=COLORS["sidebar"], fg=COLORS["subtext"],
                 font=FONTS["small"]).pack(pady=(0, 24))

        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=16, pady=4)

        # Navigation buttons
        nav_items = [
            ("🏠  Dashboard",   "dashboard"),
            ("👤  Clients",     "clients"),
            ("🛠️  Services",    "services"),
            ("📅  Reservations","reservations"),
            ("📋  Log Viewer",  "logs"),
        ]
        self._nav_buttons = {}
        for label, key in nav_items:
            btn = tk.Button(
                self.sidebar, text=label, anchor="w",
                bg=COLORS["sidebar"], fg=COLORS["text"],
                activebackground=COLORS["card"], activeforeground=COLORS["accent"],
                font=FONTS["body"], bd=0, padx=20, pady=10, cursor="hand2",
                command=lambda k=key: self._show_frame(k)
            )
            btn.pack(fill="x")
            self._nav_buttons[key] = btn

        # ---- Main content area ----------------------------------------
        self.content = tk.Frame(self, bg=COLORS["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        # Build all frames
        self._frames = {}
        self._frames["dashboard"]    = self._build_dashboard()
        self._frames["clients"]      = self._build_clients()
        self._frames["services"]     = self._build_services()
        self._frames["reservations"] = self._build_reservations()
        self._frames["logs"]         = self._build_logs()

    def _show_frame(self, key: str) -> None:
        """Show the selected frame and update nav highlight."""
        for k, frame in self._frames.items():
            frame.place_forget()
        self._frames[key].place(relx=0, rely=0, relwidth=1, relheight=1)

        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(bg=COLORS["card"], fg=COLORS["accent"])
            else:
                btn.configure(bg=COLORS["sidebar"], fg=COLORS["text"])

        # Refresh dynamic content
        if key == "dashboard":
            self._refresh_dashboard()
        elif key == "clients":
            self._refresh_clients_table()
        elif key == "services":
            self._refresh_services_table()
        elif key == "reservations":
            self._refresh_reservations_table()
        elif key == "logs":
            self._refresh_logs()

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def _build_dashboard(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg=COLORS["bg"])

        tk.Label(frame, text="Dashboard", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(anchor="w", padx=30, pady=(24, 4))
        tk.Label(frame, text="Software FJ · Management Overview",
                 bg=COLORS["bg"], fg=COLORS["subtext"], font=FONTS["body"]).pack(anchor="w", padx=30, pady=(0, 20))

        # Stats cards row
        self._stat_frame = tk.Frame(frame, bg=COLORS["bg"])
        self._stat_frame.pack(fill="x", padx=30)

        self._stat_labels = {}
        stats_def = [
            ("clients",     "👤 Clients",      COLORS["accent2"]),
            ("services",    "🛠 Services",      COLORS["accent"]),
            ("pending",     "⏳ Pending",       COLORS["pending"]),
            ("confirmed",   "✅ Confirmed",     COLORS["confirmed"]),
            ("completed",   "🏁 Completed",     COLORS["completed"]),
            ("cancelled",   "❌ Cancelled",     COLORS["cancelled"]),
        ]
        for i, (key, label, color) in enumerate(stats_def):
            card = tk.Frame(self._stat_frame, bg=COLORS["card"],
                            highlightbackground=color, highlightthickness=2)
            card.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            self._stat_frame.columnconfigure(i, weight=1)
            tk.Label(card, text=label, bg=COLORS["card"],
                     fg=color, font=FONTS["small"]).pack(pady=(12, 2))
            lbl = tk.Label(card, text="0", bg=COLORS["card"],
                           fg=COLORS["text"], font=("Segoe UI", 22, "bold"))
            lbl.pack(pady=(0, 12))
            self._stat_labels[key] = lbl

        # Recent reservations
        tk.Label(frame, text="Recent Reservations", bg=COLORS["bg"],
                 fg=COLORS["text"], font=FONTS["heading"]).pack(anchor="w", padx=30, pady=(20, 6))

        cols = ("ID", "Client", "Service", "Date", "Hours", "Status", "Cost")
        self._dash_tree = self._make_treeview(frame, cols, height=8)
        self._dash_tree.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        return frame

    def _refresh_dashboard(self) -> None:
        stats = self.system.get_stats()
        for key, lbl in self._stat_labels.items():
            lbl.configure(text=str(stats.get(key, 0)))
        # Recent reservations table
        self._dash_tree.delete(*self._dash_tree.get_children())
        for res in self.system.list_reservations():
            cost = res.calculate_total()
            self._dash_tree.insert("", "end", values=(
                f"#{res.reservation_id}",
                res.client.full_name,
                res.service.name,
                str(res.reservation_date),
                f"{res.hours}h",
                res.status.value,
                f"${cost:,.0f}",
            ), tags=(res.status.value.lower(),))
        self._apply_status_tags(self._dash_tree)

    # ------------------------------------------------------------------
    # Clients
    # ------------------------------------------------------------------

    def _build_clients(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg=COLORS["bg"])

        # Header
        hdr = tk.Frame(frame, bg=COLORS["bg"])
        hdr.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hdr, text="Clients", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left")
        tk.Button(hdr, text="＋ New Client", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=6,
                  cursor="hand2", command=self._open_add_client).pack(side="right")

        # Table
        cols = ("ID", "Full Name", "Email", "Phone")
        self._clients_tree = self._make_treeview(frame, cols, height=12)
        self._clients_tree.pack(fill="both", expand=True, padx=30)

        # Action buttons
        btn_row = tk.Frame(frame, bg=COLORS["bg"])
        btn_row.pack(fill="x", padx=30, pady=10)
        tk.Button(btn_row, text="🗑 Delete Selected", bg=COLORS["red"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=14, pady=6,
                  cursor="hand2", command=self._delete_client).pack(side="left", padx=(0, 8))

        return frame

    def _refresh_clients_table(self) -> None:
        self._clients_tree.delete(*self._clients_tree.get_children())
        for c in self.system.list_clients():
            self._clients_tree.insert("", "end", values=(
                c.client_id, c.full_name, c.email, c.phone))

    def _open_add_client(self) -> None:
        """Open dialog to register a new client."""
        win = self._make_dialog("Register New Client", 420, 380)
        fields = {}
        labels = [
            ("Client ID",   "client_id"),
            ("First Name",  "first_name"),
            ("Last Name",   "last_name"),
            ("Email",       "email"),
            ("Phone",       "phone"),
        ]
        for i, (label, key) in enumerate(labels):
            tk.Label(win, text=label, bg=COLORS["card"],
                     fg=COLORS["subtext"], font=FONTS["small"]).grid(
                row=i, column=0, sticky="w", padx=24, pady=8)
            entry = tk.Entry(win, bg=COLORS["border"], fg=COLORS["text"],
                             insertbackground=COLORS["text"], font=FONTS["body"],
                             relief="flat", width=28)
            entry.grid(row=i, column=1, padx=24, pady=8)
            fields[key] = entry

        def submit():
            try:
                cid = int(fields["client_id"].get())
            except ValueError:
                messagebox.showerror("Error", "Client ID must be a number.", parent=win)
                return
            client, err = self.system.register_client(
                cid,
                fields["first_name"].get(),
                fields["last_name"].get(),
                fields["email"].get(),
                fields["phone"].get(),
            )
            if err:
                messagebox.showerror("Validation Error", err, parent=win)
            else:
                messagebox.showinfo("Success", f"Client '{client.full_name}' registered!", parent=win)
                win.destroy()
                self._refresh_clients_table()

        tk.Button(win, text="Register Client", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=8,
                  cursor="hand2", command=submit).grid(
            row=len(labels), column=0, columnspan=2, pady=16)

    def _delete_client(self) -> None:
        sel = self._clients_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a client to delete.")
            return
        vals = self._clients_tree.item(sel[0])["values"]
        cid = int(vals[0])
        name = vals[1]
        if not messagebox.askyesno("Confirm Delete", f"Delete client '{name}' (ID {cid})?"):
            return
        ok, err = self.system.delete_client(cid)
        if err:
            messagebox.showerror("Error", err)
        else:
            messagebox.showinfo("Deleted", f"Client #{cid} deleted.")
            self._refresh_clients_table()

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------

    def _build_services(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg=COLORS["bg"])

        hdr = tk.Frame(frame, bg=COLORS["bg"])
        hdr.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hdr, text="Services", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left")
        tk.Button(hdr, text="＋ New Service", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=6,
                  cursor="hand2", command=self._open_add_service).pack(side="right")

        cols = ("Name", "Type", "Rate /h", "Details", "Available")
        self._services_tree = self._make_treeview(frame, cols, height=12)
        self._services_tree.pack(fill="both", expand=True, padx=30)

        btn_row = tk.Frame(frame, bg=COLORS["bg"])
        btn_row.pack(fill="x", padx=30, pady=10)
        tk.Button(btn_row, text="⏯ Toggle Availability", bg=COLORS["yellow"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=14, pady=6,
                  cursor="hand2", command=self._toggle_service).pack(side="left")

        return frame

    def _refresh_services_table(self) -> None:
        self._services_tree.delete(*self._services_tree.get_children())
        for svc in self.system.list_services():
            stype = svc.__class__.__name__.replace("Service", "")
            if isinstance(svc, RoomReservationService):
                details = f"Room: {svc.room_name} | Cap: {svc.capacity}"
            elif isinstance(svc, EquipmentRentalService):
                details = f"Items: {len(svc.equipment_list)}"
            else:
                details = f"{svc.specialty} | {svc.expert_name}"
            self._services_tree.insert("", "end", values=(
                svc.name,
                stype,
                f"${svc.base_cost_per_hour:,.0f}",
                details,
                "Yes" if svc.available else "No",
            ), tags=("available" if svc.available else "unavailable",))
        self._services_tree.tag_configure("available",   foreground=COLORS["green"])
        self._services_tree.tag_configure("unavailable", foreground=COLORS["red"])

    def _open_add_service(self) -> None:
        win = self._make_dialog("Add New Service", 460, 520)

        tk.Label(win, text="Service Type", bg=COLORS["card"],
                 fg=COLORS["subtext"], font=FONTS["small"]).grid(row=0, column=0, sticky="w", padx=24, pady=8)
        stype_var = tk.StringVar(value="Room Reservation")
        stype_cb = ttk.Combobox(win, textvariable=stype_var, width=26, state="readonly",
                                values=["Room Reservation", "Equipment Rental", "Consulting"])
        stype_cb.grid(row=0, column=1, padx=24, pady=8)

        base_fields = [("Service Name", "name"), ("Cost per Hour (COP)", "cost")]
        extra_frames = {}
        entries = {}

        for i, (lbl, key) in enumerate(base_fields, start=1):
            tk.Label(win, text=lbl, bg=COLORS["card"],
                     fg=COLORS["subtext"], font=FONTS["small"]).grid(row=i, column=0, sticky="w", padx=24, pady=8)
            e = tk.Entry(win, bg=COLORS["border"], fg=COLORS["text"],
                         insertbackground=COLORS["text"], font=FONTS["body"], relief="flat", width=28)
            e.grid(row=i, column=1, padx=24, pady=8)
            entries[key] = e

        # Dynamic extra fields
        extra_container = tk.Frame(win, bg=COLORS["card"])
        extra_container.grid(row=3, column=0, columnspan=2, sticky="ew", padx=24)

        def update_extras(*_):
            for w in extra_container.winfo_children():
                w.destroy()
            entries.pop("room_name", None)
            entries.pop("capacity", None)
            entries.pop("equipment", None)
            entries.pop("specialty", None)
            entries.pop("expert", None)
            entries.pop("seniority", None)

            st = stype_var.get()
            if st == "Room Reservation":
                for r, (lbl, key) in enumerate([("Room Name", "room_name"), ("Capacity", "capacity")]):
                    tk.Label(extra_container, text=lbl, bg=COLORS["card"],
                             fg=COLORS["subtext"], font=FONTS["small"]).grid(row=r, column=0, sticky="w", pady=6)
                    e = tk.Entry(extra_container, bg=COLORS["border"], fg=COLORS["text"],
                                 insertbackground=COLORS["text"], font=FONTS["body"], relief="flat", width=28)
                    e.grid(row=r, column=1, padx=8)
                    entries[key] = e
            elif st == "Equipment Rental":
                tk.Label(extra_container, text="Equipment (comma-separated)",
                         bg=COLORS["card"], fg=COLORS["subtext"], font=FONTS["small"]).grid(
                    row=0, column=0, sticky="w", pady=6)
                e = tk.Entry(extra_container, bg=COLORS["border"], fg=COLORS["text"],
                             insertbackground=COLORS["text"], font=FONTS["body"], relief="flat", width=28)
                e.grid(row=0, column=1, padx=8)
                entries["equipment"] = e
            else:
                for r, (lbl, key) in enumerate([("Specialty", "specialty"),
                                                ("Expert Name", "expert"),
                                                ("Seniority", "seniority")]):
                    tk.Label(extra_container, text=lbl, bg=COLORS["card"],
                             fg=COLORS["subtext"], font=FONTS["small"]).grid(row=r, column=0, sticky="w", pady=6)
                    if key == "seniority":
                        sv = tk.StringVar(value="mid")
                        cb = ttk.Combobox(extra_container, textvariable=sv, width=26,
                                          state="readonly", values=["junior", "mid", "senior", "lead"])
                        cb.grid(row=r, column=1, padx=8)
                        entries[key] = sv
                    else:
                        e = tk.Entry(extra_container, bg=COLORS["border"], fg=COLORS["text"],
                                     insertbackground=COLORS["text"], font=FONTS["body"], relief="flat", width=28)
                        e.grid(row=r, column=1, padx=8)
                        entries[key] = e

        stype_cb.bind("<<ComboboxSelected>>", update_extras)
        update_extras()

        def submit():
            try:
                cost = float(entries["cost"].get())
            except ValueError:
                messagebox.showerror("Error", "Cost must be a number.", parent=win)
                return
            name = entries["name"].get().strip()
            st = stype_var.get()
            try:
                if st == "Room Reservation":
                    cap_str = entries["capacity"].get()
                    try:
                        cap = int(cap_str)
                    except ValueError:
                        messagebox.showerror("Error", "Capacity must be an integer.", parent=win)
                        return
                    svc = RoomReservationService(name, cost, entries["room_name"].get(), cap)
                elif st == "Equipment Rental":
                    items = [i.strip() for i in entries["equipment"].get().split(",") if i.strip()]
                    svc = EquipmentRentalService(name, cost, items)
                else:
                    sen = entries["seniority"].get() if isinstance(entries["seniority"], str) else entries["seniority"].get()
                    svc = SpecializedConsultingService(
                        name, cost, entries["specialty"].get(), entries["expert"].get(), sen)
            except SoftwareFJBaseError as exc:
                messagebox.showerror("Validation Error", str(exc), parent=win)
                return

            _, err = self.system.add_service(svc)
            if err:
                messagebox.showerror("Error", err, parent=win)
            else:
                messagebox.showinfo("Success", f"Service '{name}' added!", parent=win)
                win.destroy()
                self._refresh_services_table()

        tk.Button(win, text="Add Service", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=8,
                  cursor="hand2", command=submit).grid(row=10, column=0, columnspan=2, pady=16)

    def _toggle_service(self) -> None:
        sel = self._services_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a service.")
            return
        name = self._services_tree.item(sel[0])["values"][0]
        ok, msg = self.system.toggle_service(name)
        if ok:
            messagebox.showinfo("Updated", msg)
        else:
            messagebox.showerror("Error", msg)
        self._refresh_services_table()

    # ------------------------------------------------------------------
    # Reservations
    # ------------------------------------------------------------------

    def _build_reservations(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg=COLORS["bg"])

        hdr = tk.Frame(frame, bg=COLORS["bg"])
        hdr.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hdr, text="Reservations", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left")
        tk.Button(hdr, text="＋ New Reservation", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=6,
                  cursor="hand2", command=self._open_add_reservation).pack(side="right")

        # Filter
        filter_row = tk.Frame(frame, bg=COLORS["bg"])
        filter_row.pack(fill="x", padx=30, pady=(0, 6))
        tk.Label(filter_row, text="Filter:", bg=COLORS["bg"],
                 fg=COLORS["subtext"], font=FONTS["small"]).pack(side="left")
        self._res_filter = tk.StringVar(value="ALL")
        for val in ["ALL", "PENDING", "CONFIRMED", "COMPLETED", "CANCELLED"]:
            tk.Radiobutton(filter_row, text=val, variable=self._res_filter,
                           value=val, bg=COLORS["bg"], fg=COLORS["text"],
                           selectcolor=COLORS["card"], activebackground=COLORS["bg"],
                           font=FONTS["small"],
                           command=self._refresh_reservations_table).pack(side="left", padx=8)

        cols = ("ID", "Client", "Service", "Date", "Hours", "Status", "Cost")
        self._res_tree = self._make_treeview(frame, cols, height=10)
        self._res_tree.pack(fill="both", expand=True, padx=30)

        btn_row = tk.Frame(frame, bg=COLORS["bg"])
        btn_row.pack(fill="x", padx=30, pady=10)
        tk.Button(btn_row, text="✅ Confirm", bg=COLORS["confirmed"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._confirm_res).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="🏁 Complete", bg=COLORS["completed"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._complete_res).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="❌ Cancel", bg=COLORS["red"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._cancel_res).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="💰 Cost Details", bg=COLORS["yellow"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._cost_details).pack(side="left")

        return frame

    def _refresh_reservations_table(self) -> None:
        self._res_tree.delete(*self._res_tree.get_children())
        filt = self._res_filter.get()
        status_map = {s.value: s for s in ReservationStatus}
        sf = status_map.get(filt)
        for res in self.system.list_reservations(sf):
            cost = res.calculate_total()
            self._res_tree.insert("", "end", iid=str(res.reservation_id), values=(
                f"#{res.reservation_id}",
                res.client.full_name,
                res.service.name,
                str(res.reservation_date),
                f"{res.hours}h",
                res.status.value,
                f"${cost:,.0f}",
            ), tags=(res.status.value.lower(),))
        self._apply_status_tags(self._res_tree)

    def _get_selected_res_id(self):
        sel = self._res_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a reservation.")
            return None
        return int(sel[0])

    def _confirm_res(self):
        rid = self._get_selected_res_id()
        if rid is None:
            return
        ok, msg = self.system.confirm_reservation(rid)
        (messagebox.showinfo if ok else messagebox.showerror)("Result", msg)
        self._refresh_reservations_table()

    def _complete_res(self):
        rid = self._get_selected_res_id()
        if rid is None:
            return
        ok, msg = self.system.complete_reservation(rid)
        (messagebox.showinfo if ok else messagebox.showerror)("Result", msg)
        self._refresh_reservations_table()

    def _cancel_res(self):
        rid = self._get_selected_res_id()
        if rid is None:
            return
        ok, msg = self.system.cancel_reservation(rid)
        (messagebox.showinfo if ok else messagebox.showerror)("Result", msg)
        self._refresh_reservations_table()

    def _cost_details(self):
        rid = self._get_selected_res_id()
        if rid is None:
            return
        res = self.system._reservations.get(rid)
        if not res:
            return
        win = self._make_dialog("Cost Breakdown", 380, 300)
        tk.Label(win, text=f"Reservation #{rid} – {res.service.name}",
                 bg=COLORS["card"], fg=COLORS["accent"], font=FONTS["heading"]).pack(pady=(16, 8))

        rows = [
            ("Default (19% tax)", res.calculate_total()),
            ("5% tax (exempt)",   res.calculate_total(tax_rate=0.05)),
            ("10% discount",      res.calculate_total(discount_pct=10)),
            ("20% disc + 5% tax", res.calculate_total(tax_rate=0.05, discount_pct=20)),
        ]
        for label, cost in rows:
            row = tk.Frame(win, bg=COLORS["card"])
            row.pack(fill="x", padx=24, pady=4)
            tk.Label(row, text=label, bg=COLORS["card"],
                     fg=COLORS["subtext"], font=FONTS["small"]).pack(side="left")
            tk.Label(row, text=f"${cost:,.2f} COP", bg=COLORS["card"],
                     fg=COLORS["green"], font=FONTS["body"]).pack(side="right")

    def _open_add_reservation(self):
        win = self._make_dialog("New Reservation", 440, 420)

        clients = self.system.list_clients()
        services = self.system.list_services()
        if not clients:
            messagebox.showwarning("No Clients", "Register at least one client first.", parent=win)
            win.destroy()
            return
        if not services:
            messagebox.showwarning("No Services", "Add at least one service first.", parent=win)
            win.destroy()
            return

        client_options = [f"{c.client_id} – {c.full_name}" for c in clients]
        service_options = [s.name for s in services]

        fields_def = [
            ("Client",          "client",  "combo", client_options),
            ("Service",         "service", "combo", service_options),
            ("Date (YYYY-MM-DD)","date",   "entry", None),
            ("Duration (hours)", "hours",  "entry", None),
            ("Notes",           "notes",   "entry", None),
        ]
        entries = {}
        for i, (lbl, key, wtype, opts) in enumerate(fields_def):
            tk.Label(win, text=lbl, bg=COLORS["card"],
                     fg=COLORS["subtext"], font=FONTS["small"]).grid(
                row=i, column=0, sticky="w", padx=24, pady=8)
            if wtype == "combo":
                var = tk.StringVar(value=opts[0])
                cb = ttk.Combobox(win, textvariable=var, values=opts,
                                  state="readonly", width=27)
                cb.grid(row=i, column=1, padx=24, pady=8)
                entries[key] = var
            else:
                e = tk.Entry(win, bg=COLORS["border"], fg=COLORS["text"],
                             insertbackground=COLORS["text"], font=FONTS["body"],
                             relief="flat", width=29)
                if key == "date":
                    e.insert(0, str(date.today()))
                e.grid(row=i, column=1, padx=24, pady=8)
                entries[key] = e

        def submit():
            try:
                cid = int(entries["client"].get().split("–")[0].strip())
            except Exception:
                messagebox.showerror("Error", "Select a valid client.", parent=win)
                return
            svc_name = entries["service"].get()
            date_str = entries["date"].get() if isinstance(entries["date"], tk.Entry) else entries["date"].get()
            try:
                from datetime import date as dclass
                res_date = dclass.fromisoformat(date_str)
            except ValueError:
                messagebox.showerror("Error", "Date must be YYYY-MM-DD format.", parent=win)
                return
            try:
                hours = float(entries["hours"].get())
            except ValueError:
                messagebox.showerror("Error", "Duration must be a number.", parent=win)
                return
            notes = entries["notes"].get() if isinstance(entries["notes"], tk.Entry) else ""

            res, err = self.system.create_reservation(cid, svc_name, res_date, hours, notes)
            if err:
                messagebox.showerror("Error", err, parent=win)
            else:
                cost = res.calculate_total()
                messagebox.showinfo("Success",
                    f"Reservation #{res.reservation_id} created!\nTotal: ${cost:,.2f} COP", parent=win)
                win.destroy()
                self._refresh_reservations_table()

        tk.Button(win, text="Create Reservation", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=8,
                  cursor="hand2", command=submit).grid(
            row=len(fields_def), column=0, columnspan=2, pady=16)

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    def _build_logs(self) -> tk.Frame:
        frame = tk.Frame(self.content, bg=COLORS["bg"])

        hdr = tk.Frame(frame, bg=COLORS["bg"])
        hdr.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hdr, text="Event Log", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left")
        tk.Button(hdr, text="🔄 Refresh", bg=COLORS["card"],
                  fg=COLORS["text"], font=FONTS["btn"], bd=0, padx=14, pady=6,
                  cursor="hand2", command=self._refresh_logs).pack(side="right")

        self._log_text = scrolledtext.ScrolledText(
            frame, bg=COLORS["card"], fg=COLORS["text"],
            font=FONTS["mono"], relief="flat", state="disabled")
        self._log_text.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        return frame

    def _refresh_logs(self) -> None:
        content = self.system.get_log()
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.insert("end", content)
        self._log_text.configure(state="disabled")
        self._log_text.see("end")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_treeview(self, parent, columns, height=10) -> ttk.Treeview:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=COLORS["card"],
                        foreground=COLORS["text"],
                        fieldbackground=COLORS["card"],
                        rowheight=28,
                        font=FONTS["small"])
        style.configure("Treeview.Heading",
                        background=COLORS["border"],
                        foreground=COLORS["accent"],
                        font=FONTS["small"])
        style.map("Treeview", background=[("selected", COLORS["border"])])

        tree = ttk.Treeview(parent, columns=columns, show="headings", height=height)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=120)
        sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        return tree

    def _apply_status_tags(self, tree) -> None:
        tree.tag_configure("pending",   foreground=COLORS["pending"])
        tree.tag_configure("confirmed", foreground=COLORS["confirmed"])
        tree.tag_configure("completed", foreground=COLORS["completed"])
        tree.tag_configure("cancelled", foreground=COLORS["cancelled"])

    def _make_dialog(self, title: str, w: int, h: int) -> tk.Toplevel:
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry(f"{w}x{h}")
        win.configure(bg=COLORS["card"])
        win.resizable(False, False)
        win.grab_set()
        return win

    # ------------------------------------------------------------------
    # Demo data
    # ------------------------------------------------------------------

    def _load_demo_data(self) -> None:
        """Pre-load sample clients, services and reservations."""
        # Clients
        self.system.register_client(101, "Andrés", "Martínez", "andres@softwarefj.com", "+57 300 123 4567")
        self.system.register_client(102, "Laura", "Gómez", "laura@softwarefj.com", "3101234567")
        self.system.register_client(103, "Carlos", "Ruiz", "carlos@empresa.co", "+57 310 987 6543")

        # Services
        room = RoomReservationService("Conference Room A", 80_000, "Sala Innovación", 12)
        equip = EquipmentRentalService("Tech Pack Pro", 25_000, ["Laptop Dell", "Projector", "HDMI Hub"])
        consult = SpecializedConsultingService("Cybersecurity Advisory", 150_000,
                                               "Cybersecurity", "Dra. Ana Fernández", "senior")
        for svc in [room, equip, consult]:
            self.system.add_service(svc)

        # Reservations
        from datetime import timedelta
        today = date.today()
        self.system.create_reservation(101, "Conference Room A", today + timedelta(7), 3, "Q3 planning")
        self.system.create_reservation(102, "Tech Pack Pro", today + timedelta(7), 8, "Product demo")
        res3, _ = self.system.create_reservation(103, "Cybersecurity Advisory", today + timedelta(14), 2)
        if res3:
            self.system.confirm_reservation(res3.reservation_id)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    app = SoftwareFJApp()
    app.mainloop()
