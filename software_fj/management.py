# =============================================================================
# management.py — Orquestador central de la lógica de negocio de Software FJ
# =============================================================================
# ManagementSystem centraliza todas las operaciones sobre clientes, servicios
# y reservas. Atrapa internamente todas las excepciones del dominio y retorna
# tuplas (resultado, error) para que la GUI o los tests puedan reaccionar
# sin manejar excepciones directamente.
# =============================================================================

from datetime import date
from typing import Dict, List, Optional

from clients import Client
from services import Service
from reservations import Reservation, ReservationStatus
from exceptions import (
    SoftwareFJBaseError, DuplicateClientError, InvalidParameterError,
    ReservationError, ReservationConflictError
)
from logs import EventLogger


class ManagementSystem:
    """
    Orquestador central del sistema Software FJ.

    Responsabilidades:
        - Registrar, listar y eliminar clientes.
        - Agregar, listar y cambiar disponibilidad de servicios.
        - Crear, confirmar, completar y cancelar reservas.
        - Exponer estadísticas y el log de eventos.

    Todos los métodos capturan excepciones internamente y retornan
    tuplas de la forma (resultado, mensaje_error). Si la operación
    falla, resultado será None o False y mensaje_error tendrá el texto.
    """

    def __init__(self) -> None:
        # Diccionarios indexados por su llave natural (client_id, service_name, res_id)
        self._clients: Dict[int, Client]          = {}
        self._services: Dict[str, Service]        = {}
        self._reservations: Dict[int, Reservation] = {}
        self._logger      = EventLogger("logs/software_fj.log")
        self._next_res_id = 1   # Contador auto-incremental para IDs de reserva
        self._logger.info("Software FJ iniciado.")

    # =========================================================================
    # CLIENTES
    # =========================================================================

    def register_client(self, client_id: int, first_name: str, last_name: str,
                        email: str, phone: str):
        """
        Registra un nuevo cliente en el sistema.

        Retorna:
            (Client, None)       — si el registro fue exitoso.
            (None, str_error)    — si la validación o duplicado falló.
        """
        try:
            if client_id in self._clients:
                raise DuplicateClientError(client_id)
            client = Client(client_id, first_name, last_name, email, phone)
            self._clients[client_id] = client
            self._logger.info(f"CLIENTE REGISTRADO: {client.describe()}")
            return client, None
        except SoftwareFJBaseError as exc:
            self._logger.error(f"ERROR CLIENTE: {exc}", exc)
            return None, str(exc)
        except Exception as exc:
            # Captura errores inesperados para no crashear la GUI
            self._logger.error(f"ERROR INESPERADO CLIENTE: {exc}", exc)
            return None, str(exc)

    def list_clients(self) -> List[Client]:
        """Retorna todos los clientes ordenados por client_id."""
        return sorted(self._clients.values(), key=lambda c: c.client_id)

    def delete_client(self, client_id: int):
        """
        Elimina un cliente del sistema.
        No se permite eliminar un cliente con reservas activas (PENDING o CONFIRMED).

        Retorna:
            (True, None)      — si la eliminación fue exitosa.
            (False, str_error) — si el cliente no existe o tiene reservas activas.
        """
        try:
            if client_id not in self._clients:
                raise InvalidParameterError("client_id", client_id, "no encontrado")
            # Verifica que no haya reservas activas antes de eliminar
            for res in self._reservations.values():
                if res.client.client_id == client_id and res.status in (
                        ReservationStatus.PENDING, ReservationStatus.CONFIRMED):
                    raise ReservationError(
                        f"No se puede eliminar el cliente #{client_id}: tiene reservas activas.")
            del self._clients[client_id]
            self._logger.info(f"CLIENTE ELIMINADO: id={client_id}")
            return True, None
        except SoftwareFJBaseError as exc:
            self._logger.error(f"ERROR ELIMINAR CLIENTE: {exc}", exc)
            return False, str(exc)

    # =========================================================================
    # SERVICIOS
    # =========================================================================

    def add_service(self, service: Service):
        """
        Agrega un nuevo servicio al catálogo.
        No se permiten servicios con el mismo nombre.

        Retorna:
            (Service, None)    — si la adición fue exitosa.
            (None, str_error)  — si el servicio ya existe o la validación falla.
        """
        try:
            if service.name in self._services:
                raise SoftwareFJBaseError(f"El servicio '{service.name}' ya existe.")
            self._services[service.name] = service
            self._logger.info(f"SERVICIO AGREGADO: {service.describe()}")
            return service, None
        except SoftwareFJBaseError as exc:
            self._logger.error(f"ERROR SERVICIO: {exc}", exc)
            return None, str(exc)
        except Exception as exc:
            self._logger.error(f"ERROR INESPERADO SERVICIO: {exc}", exc)
            return None, str(exc)

    def list_services(self) -> List[Service]:
        """Retorna todos los servicios ordenados por nombre."""
        return sorted(self._services.values(), key=lambda s: s.name)

    def toggle_service(self, name: str):
        """
        Cambia la disponibilidad de un servicio (disponible ↔ no disponible).

        Retorna:
            (True, str_info)   — con mensaje del nuevo estado.
            (False, str_error) — si el servicio no fue encontrado.
        """
        try:
            svc = self._services.get(name)
            if not svc:
                raise InvalidParameterError("name", name, "servicio no encontrado")
            svc.available = not svc.available
            estado = "habilitado" if svc.available else "deshabilitado"
            self._logger.info(f"SERVICIO {estado.upper()}: '{name}'")
            return True, f"El servicio '{name}' ahora está {estado}."
        except SoftwareFJBaseError as exc:
            return False, str(exc)

    # =========================================================================
    # RESERVAS
    # =========================================================================

    def create_reservation(self, client_id: int, service_name: str,
                           reservation_date: date, hours: float, notes: str = ""):
        """
        Crea una nueva reserva después de verificar conflictos.

        Retorna:
            (Reservation, None)  — si la reserva fue creada exitosamente.
            (None, str_error)    — si el cliente/servicio no existe,
                                   hay un conflicto de fechas o la duración es inválida.
        """
        try:
            # Verifica que el cliente exista
            client = self._clients.get(client_id)
            if not client:
                raise InvalidParameterError("client_id", client_id, "cliente no encontrado")

            # Verifica que el servicio exista
            service = self._services.get(service_name)
            if not service:
                raise InvalidParameterError("service_name", service_name, "servicio no encontrado")

            # Detecta conflictos: misma fecha, mismo cliente, mismo servicio activo
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
                f"RESERVA CREADA: #{reservation.reservation_id} | "
                f"Cliente #{client_id} | '{service_name}' | {reservation_date} | {hours}h | ${cost:,.2f}")
            return reservation, None

        except SoftwareFJBaseError as exc:
            self._logger.error(f"ERROR RESERVA: {exc}", exc)
            return None, str(exc)
        except Exception as exc:
            self._logger.error(f"ERROR INESPERADO RESERVA: {exc}", exc)
            return None, str(exc)

    def confirm_reservation(self, res_id: int):
        """
        Confirma una reserva en estado PENDING.

        Retorna:
            (True, str_info)   — si la confirmación fue exitosa.
            (False, str_error) — si la reserva no existe o no está en PENDING.
        """
        try:
            res = self._reservations.get(res_id)
            if not res:
                raise InvalidParameterError("reservation_id", res_id, "no encontrada")
            res.confirm()
            self._logger.info(f"RESERVA CONFIRMADA: #{res_id}")
            return True, f"Reserva #{res_id} confirmada."
        except SoftwareFJBaseError as exc:
            self._logger.error(f"ERROR CONFIRMAR: {exc}", exc)
            return False, str(exc)

    def complete_reservation(self, res_id: int):
        """
        Marca una reserva como completada. Solo válido desde CONFIRMED.

        Retorna:
            (True, str_info)   — si la completación fue exitosa.
            (False, str_error) — si la reserva no existe o no está en CONFIRMED.
        """
        try:
            res = self._reservations.get(res_id)
            if not res:
                raise InvalidParameterError("reservation_id", res_id, "no encontrada")
            res.complete()
            self._logger.info(f"RESERVA COMPLETADA: #{res_id}")
            return True, f"Reserva #{res_id} completada."
        except SoftwareFJBaseError as exc:
            self._logger.error(f"ERROR COMPLETAR: {exc}", exc)
            return False, str(exc)

    def cancel_reservation(self, res_id: int, reason: str = "Cancelada por el usuario."):
        """
        Cancela una reserva con un motivo opcional.
        No se puede cancelar una reserva ya COMPLETED o CANCELLED.

        Retorna:
            (True, str_info)   — si la cancelación fue exitosa.
            (False, str_error) — si la reserva no existe o el estado no lo permite.
        """
        try:
            res = self._reservations.get(res_id)
            if not res:
                raise InvalidParameterError("reservation_id", res_id, "no encontrada")
            res.cancel(reason)
            self._logger.info(f"RESERVA CANCELADA: #{res_id}")
            return True, f"Reserva #{res_id} cancelada."
        except SoftwareFJBaseError as exc:
            self._logger.error(f"ERROR CANCELAR: {exc}", exc)
            return False, str(exc)

    def list_reservations(self, status_filter: ReservationStatus = None) -> List[Reservation]:
        """
        Retorna reservas ordenadas por ID.
        Si se provee status_filter, solo retorna reservas con ese estado.
        """
        result = sorted(self._reservations.values(), key=lambda r: r.reservation_id)
        if status_filter:
            result = [r for r in result if r.status == status_filter]
        return result

    # =========================================================================
    # ESTADÍSTICAS Y LOG
    # =========================================================================

    def get_log(self) -> str:
        """Retorna el contenido completo del archivo de log."""
        return self._logger.read_log()

    def get_stats(self) -> dict:
        """
        Retorna un diccionario con estadísticas del sistema:
        número de clientes, servicios, reservas por estado.
        """
        total     = len(self._reservations)
        by_status = {s: 0 for s in ReservationStatus}
        for r in self._reservations.values():
            by_status[r.status] += 1
        return {
            "clientes":    len(self._clients),
            "servicios":   len(self._services),
            "reservas":    total,
            "pendientes":  by_status[ReservationStatus.PENDING],
            "confirmadas": by_status[ReservationStatus.CONFIRMED],
            "completadas": by_status[ReservationStatus.COMPLETED],
            "canceladas":  by_status[ReservationStatus.CANCELLED],
        }
