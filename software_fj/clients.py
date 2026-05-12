# =============================================================================
# clients.py — Módulo de gestión de clientes para Software FJ
# =============================================================================
# Define la clase Client con validación estricta de todos sus campos.
# Hereda de BaseEntity (definida en services.py vía el módulo base).
# =============================================================================

import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from exceptions import ClientValidationError


# Expresiones regulares para validar email y teléfono
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_RE = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")


# =============================================================================
# ENTIDAD BASE (abstract)
# =============================================================================

class BaseEntity(ABC):
    """
    Clase raíz abstracta para todas las entidades del dominio.
    Genera automáticamente un UUID interno y registra la fecha de creación.
    Todas las subclases deben implementar validate() y describe().
    """

    def __init__(self) -> None:
        self._entity_id  = str(uuid.uuid4())   # Identificador único interno
        self._created_at = datetime.now()       # Fecha/hora de creación

    @abstractmethod
    def validate(self) -> None:
        """Valida el estado interno. Lanza excepción si hay datos inválidos."""

    @abstractmethod
    def describe(self) -> str:
        """Retorna una descripción legible de la entidad."""

    def __str__(self) -> str:
        return self.describe()


# =============================================================================
# CLIENTE
# =============================================================================

class Client(BaseEntity):
    """
    Representa un cliente registrado en el sistema.

    Parámetros:
        client_id  : Número entero positivo único del cliente.
        first_name : Nombre (mín. 2 caracteres, debe contener letras).
        last_name  : Apellido (mismas restricciones que first_name).
        email      : Dirección de correo válida (formato RFC básico).
        phone      : Número de teléfono (7-20 dígitos, acepta +, espacios, guiones).

    La validación se ejecuta automáticamente en __init__ y lanza
    ClientValidationError si algún campo es inválido.
    """

    def __init__(self, client_id: int, first_name: str, last_name: str,
                 email: str, phone: str) -> None:
        super().__init__()
        self._client_id  = client_id
        self._first_name = first_name
        self._last_name  = last_name
        self._email      = email
        self._phone      = phone
        self.validate()  # Falla rápido si algún dato es inválido

    def validate(self) -> None:
        """Valida todos los campos del cliente. Lanza ClientValidationError si falla."""

        # Validación del ID: debe ser entero positivo (no bool)
        if not isinstance(self._client_id, int) or isinstance(self._client_id, bool):
            raise ClientValidationError("client_id debe ser un entero.")
        if self._client_id <= 0:
            raise ClientValidationError("client_id debe ser mayor a 0.")

        # Validación de nombres: no vacíos, mín. 2 chars, al menos una letra
        for field, value in [("first_name", self._first_name), ("last_name", self._last_name)]:
            if not isinstance(value, str) or not value.strip():
                raise ClientValidationError(f"{field} no puede estar vacío.")
            if len(value.strip()) < 2:
                raise ClientValidationError(f"{field} es demasiado corto (mín. 2 caracteres).")
            if not any(c.isalpha() for c in value):
                raise ClientValidationError(f"{field} debe contener al menos una letra.")

        # Validación de email con expresión regular
        if not _EMAIL_RE.match(self._email.strip()):
            raise ClientValidationError(f"'{self._email}' no es una dirección de email válida.")

        # Validación de teléfono con expresión regular
        if not _PHONE_RE.match(self._phone.strip()):
            raise ClientValidationError(f"'{self._phone}' no es un número de teléfono válido.")

    def describe(self) -> str:
        return (f"[#{self._client_id}] {self._first_name} {self._last_name} "
                f"| {self._email} | {self._phone}")

    # -----------------------------------------------------------------------
    # Propiedades de solo lectura
    # -----------------------------------------------------------------------

    @property
    def client_id(self) -> int:
        """ID numérico único del cliente."""
        return self._client_id

    @property
    def full_name(self) -> str:
        """Nombre completo del cliente (nombre + apellido)."""
        return f"{self._first_name} {self._last_name}"

    @property
    def email(self) -> str:
        return self._email

    @property
    def phone(self) -> str:
        return self._phone
