# =============================================================================
# tests/test_simulation.py — Casos de prueba automáticos para Software FJ
# =============================================================================
# Este módulo demuestra operaciones válidas e inválidas del sistema sin
# necesidad de la interfaz gráfica. Ejecutar con:
#
#     cd software_fj && python tests/test_simulation.py
#
# Cada caso imprime PASÓ ✓ o FALLÓ ✗ con detalles del resultado.
# =============================================================================

import sys
import os

# Permite importar los módulos desde la carpeta padre (software_fj/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta

from management import ManagementSystem
from services import (
    RoomReservationService, EquipmentRentalService, SpecializedConsultingService
)
from reservations import ReservationStatus
from exceptions import (
    ClientValidationError, DuplicateClientError, ServiceValidationError,
    InvalidDurationError, ServiceNotAvailableError, ReservationConflictError
)


# =============================================================================
# Utilidad de reporte
# =============================================================================

_passed = 0
_failed = 0


def check(description: str, condition: bool, extra: str = "") -> None:
    """Imprime el resultado de un caso de prueba y acumula contadores."""
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  PASÓ  ✓  {description}")
    else:
        _failed += 1
        detail = f" → {extra}" if extra else ""
        print(f"  FALLÓ ✗  {description}{detail}")


def section(title: str) -> None:
    """Imprime un encabezado de sección para mejor legibilidad."""
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# =============================================================================
# SECCIÓN 1: Registro válido de clientes
# =============================================================================

def test_registro_clientes_valido():
    section("1. Registro válido de clientes")
    sys = ManagementSystem()

    client, err = sys.register_client(101, "Andrés", "Martínez", "andres@fj.com", "+57 300 123 4567")
    check("Registrar cliente con datos válidos", client is not None and err is None)

    client2, err2 = sys.register_client(102, "Laura", "Gómez", "laura@fj.com", "3101234567")
    check("Registrar segundo cliente", client2 is not None and err2 is None)

    clientes = sys.list_clients()
    check("list_clients retorna 2 clientes", len(clientes) == 2)

    return sys  # Retorna el sistema con clientes para reutilizar


# =============================================================================
# SECCIÓN 2: Registro inválido de clientes (casos de error)
# =============================================================================

def test_registro_clientes_invalido():
    section("2. Registro inválido de clientes (validaciones)")
    sys = ManagementSystem()

    # Email inválido
    _, err = sys.register_client(201, "Pedro", "López", "no-es-email", "3000000000")
    check("Email inválido debe fallar", err is not None, err)

    # Nombre vacío
    _, err = sys.register_client(202, "", "Ruiz", "pedro@fj.com", "3000000000")
    check("Nombre vacío debe fallar", err is not None, err)

    # ID duplicado
    sys.register_client(203, "Ana", "Torres", "ana@fj.com", "3100000000")
    _, err = sys.register_client(203, "Otro", "Cliente", "otro@fj.com", "3100000001")
    check("ID duplicado debe fallar", err is not None, err)

    # Teléfono inválido
    _, err = sys.register_client(204, "Luis", "Díaz", "luis@fj.com", "abc")
    check("Teléfono inválido debe fallar", err is not None, err)

    # client_id = 0 (no positivo)
    _, err = sys.register_client(0, "Zero", "User", "zero@fj.com", "3000000000")
    check("client_id = 0 debe fallar", err is not None, err)


# =============================================================================
# SECCIÓN 3: Creación válida de servicios
# =============================================================================

def test_servicios_validos():
    section("3. Creación válida de servicios")

    sala = RoomReservationService("Sala Innovación", 80_000, "Piso 3 - Sala A", 12)
    check("Crear RoomReservationService válido", sala is not None)
    check("Nombre correcto", sala.name == "Sala Innovación")

    equipo = EquipmentRentalService("Tech Pack Pro", 25_000, ["Laptop", "Proyector", "HDMI"])
    check("Crear EquipmentRentalService válido", equipo is not None)
    check("Lista de equipos correcta", len(equipo.equipment_list) == 3)

    consultoria = SpecializedConsultingService(
        "Consultoría Cyber", 150_000, "Ciberseguridad", "Dra. Ana Fernández", "senior")
    check("Crear SpecializedConsultingService válido", consultoria is not None)
    check("Seniority correcta", consultoria.seniority == "senior")


# =============================================================================
# SECCIÓN 4: Creación inválida de servicios
# =============================================================================

def test_servicios_invalidos():
    section("4. Creación inválida de servicios (validaciones)")

    # Costo negativo
    try:
        RoomReservationService("Sala X", -100, "Sala A", 10)
        check("Costo negativo debe fallar", False)
    except Exception as e:
        check("Costo negativo lanza excepción", True, str(e))

    # Nombre vacío
    try:
        EquipmentRentalService("", 25_000, ["Laptop"])
        check("Nombre vacío debe fallar", False)
    except Exception as e:
        check("Nombre vacío lanza excepción", True, str(e))

    # Lista de equipos vacía
    try:
        EquipmentRentalService("Pack Vacío", 25_000, [])
        check("Lista vacía debe fallar", False)
    except Exception as e:
        check("Lista de equipos vacía lanza excepción", True, str(e))

    # Seniority inválida
    try:
        SpecializedConsultingService("Consult", 100_000, "TI", "Expert", seniority="experto")
        check("Seniority inválida debe fallar", False)
    except Exception as e:
        check("Seniority inválida lanza excepción", True, str(e))


# =============================================================================
# SECCIÓN 5: Flujo completo de reserva válida
# =============================================================================

def test_flujo_reserva_valido():
    section("5. Flujo completo: PENDING → CONFIRMED → COMPLETED")
    sistema = ManagementSystem()

    # Setup
    sistema.register_client(301, "Carlos", "Ruiz", "carlos@fj.com", "+57 310 987 6543")
    sala = RoomReservationService("Sala Boardroom", 90_000, "Piso 5", 20)
    sistema.add_service(sala)

    fecha = date.today() + timedelta(days=7)

    # Crear reserva
    res, err = sistema.create_reservation(301, "Sala Boardroom", fecha, 3.0, "Reunión Q4")
    check("Crear reserva válida", res is not None and err is None)
    check("Estado inicial = PENDING", res is not None and res.status == ReservationStatus.PENDING)

    # Confirmar
    ok, msg = sistema.confirm_reservation(res.reservation_id)
    check("Confirmar reserva", ok is True)
    check("Estado = CONFIRMED", res.status == ReservationStatus.CONFIRMED)

    # Completar
    ok, msg = sistema.complete_reservation(res.reservation_id)
    check("Completar reserva", ok is True)
    check("Estado = COMPLETED", res.status == ReservationStatus.COMPLETED)

    # Verificar costo calculado
    costo = res.calculate_total()
    check("Costo calculado > 0", costo > 0)

    return sistema, res


# =============================================================================
# SECCIÓN 6: Casos inválidos de reserva
# =============================================================================

def test_reservas_invalidas():
    section("6. Reservas inválidas (conflictos y errores de estado)")
    sistema = ManagementSystem()

    # Setup
    sistema.register_client(401, "María", "López", "maria@fj.com", "3204567890")
    equipo = EquipmentRentalService("Pack Demo", 20_000, ["Laptop", "Proyector"])
    sistema.add_service(equipo)
    fecha = date.today() + timedelta(days=10)

    # Crear primera reserva
    res, _ = sistema.create_reservation(401, "Pack Demo", fecha, 4.0)
    check("Primera reserva creada", res is not None)

    # Conflicto: misma reserva
    res2, err2 = sistema.create_reservation(401, "Pack Demo", fecha, 4.0)
    check("Reserva duplicada debe fallar", res2 is None and err2 is not None, err2)

    # Duración fuera de rango (EquipmentRental: 2-24h)
    res3, err3 = sistema.create_reservation(401, "Pack Demo", fecha + timedelta(1), 1.0)
    check("Duración menor al mínimo debe fallar", res3 is None and err3 is not None, err3)

    res4, err4 = sistema.create_reservation(401, "Pack Demo", fecha + timedelta(2), 25.0)
    check("Duración mayor al máximo debe fallar", res4 is None and err4 is not None, err4)

    # Completar sin confirmar primero
    ok, msg = sistema.complete_reservation(res.reservation_id)
    check("Completar reserva PENDING debe fallar", ok is False, msg)

    # Cancelar y luego intentar confirmar
    sistema.cancel_reservation(res.reservation_id)
    ok, msg = sistema.confirm_reservation(res.reservation_id)
    check("Confirmar reserva CANCELLED debe fallar", ok is False, msg)

    # Cliente inexistente
    _, err = sistema.create_reservation(9999, "Pack Demo", fecha + timedelta(5), 4.0)
    check("Reserva con cliente inexistente debe fallar", err is not None, err)


# =============================================================================
# SECCIÓN 7: Servicio no disponible
# =============================================================================

def test_servicio_no_disponible():
    section("7. Reserva con servicio deshabilitado")
    sistema = ManagementSystem()

    sistema.register_client(501, "Jorge", "Vargas", "jorge@fj.com", "3150000000")
    consult = SpecializedConsultingService(
        "Consult IA", 200_000, "Inteligencia Artificial", "Dr. Smith", "lead")
    sistema.add_service(consult)

    # Deshabilitar el servicio
    sistema.toggle_service("Consult IA")
    check("Servicio deshabilitado", not sistema.list_services()[0].available)

    # Intentar reservar servicio deshabilitado
    res, err = sistema.create_reservation(501, "Consult IA", date.today() + timedelta(3), 2.0)
    check("Reserva en servicio no disponible debe fallar", res is None and err is not None, err)

    # Rehabilitar y reservar
    sistema.toggle_service("Consult IA")
    res2, err2 = sistema.create_reservation(501, "Consult IA", date.today() + timedelta(3), 2.0)
    check("Reserva después de habilitar servicio es exitosa", res2 is not None and err2 is None)


# =============================================================================
# SECCIÓN 8: Verificación de estadísticas
# =============================================================================

def test_estadisticas():
    section("8. Estadísticas del sistema")
    sistema = ManagementSystem()

    sistema.register_client(601, "Sofia", "Mendez", "sofia@fj.com", "3170000000")
    sala = RoomReservationService("Sala Stats", 50_000, "Piso 2", 10)
    sistema.add_service(sala)

    fecha = date.today() + timedelta(days=5)
    r1, _ = sistema.create_reservation(601, "Sala Stats", fecha, 2.0)
    r2, _ = sistema.create_reservation(601, "Sala Stats", fecha + timedelta(1), 3.0)

    sistema.confirm_reservation(r1.reservation_id)
    sistema.cancel_reservation(r2.reservation_id)

    stats = sistema.get_stats()
    check("Stats: 1 cliente",    stats["clientes"] == 1)
    check("Stats: 1 servicio",   stats["servicios"] == 1)
    check("Stats: 2 reservas",   stats["reservas"] == 2)
    check("Stats: 1 confirmada", stats["confirmadas"] == 1)
    check("Stats: 1 cancelada",  stats["canceladas"] == 1)


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  SOFTWARE FJ — SIMULACIÓN AUTOMÁTICA DE CASOS DE PRUEBA")
    print("=" * 60)

    test_registro_clientes_valido()
    test_registro_clientes_invalido()
    test_servicios_validos()
    test_servicios_invalidos()
    test_flujo_reserva_valido()
    test_reservas_invalidas()
    test_servicio_no_disponible()
    test_estadisticas()

    # Resumen final
    total = _passed + _failed
    print(f"\n{'=' * 60}")
    print(f"  RESULTADO: {_passed}/{total} pruebas pasaron  |  {_failed} fallaron")
    print("=" * 60)

    # Código de salida 0 si todo pasó, 1 si hubo fallas (útil en CI)
    sys.exit(0 if _failed == 0 else 1)
