# Software FJ — Sistema de Gestión Integrado
**Estudiante:** Jean Pool Muñoz Amaya | **Grupo:** 371 | **UNAD**

---

## Estructura del proyecto

```
software_fj/
│
├── exceptions.py          # Excepciones personalizadas del dominio
├── logs.py                # Sistema de logging con bloques finally
├── clients.py             # Clase Client + BaseEntity (ABC)
├── services.py            # Servicios: Sala, Equipo, Consultoría
├── reservations.py        # Clase Reservation + ReservationStatus
├── management.py          # Orquestador de lógica de negocio
├── app.py                 # Interfaz gráfica Tkinter (punto de entrada)
│
├── tests/
│   └── test_simulation.py # Casos de prueba automáticos (válidos e inválidos)
│
└── logs/
    └── software_fj.log    # Generado automáticamente al ejecutar
```

---

## Cómo ejecutar

### Interfaz gráfica
```bash
cd software_fj
python app.py
```

### Simulación automática de casos de prueba
```bash
cd software_fj
python tests/test_simulation.py
```

---

## Mejoras aplicadas (según retroalimentación)

### 1. Separación en módulos independientes
El código fue dividido en 6 módulos con responsabilidades claramente separadas:
- `exceptions.py` — jerarquía de excepciones
- `logs.py` — registro de eventos
- `clients.py` — entidad Cliente
- `services.py` — entidades de Servicio
- `reservations.py` — entidad Reserva
- `management.py` — lógica de negocio central

### 2. Uso de bloques `finally`
El módulo `logs.py` implementa el patrón solicitado en todos los métodos
de lectura/escritura de archivos:

```python
archivo = None
try:
    archivo = open(self._log_path, "a", encoding="utf-8")
    archivo.write(entry)
except OSError:
    print(entry)
finally:
    # Siempre se ejecuta: cierra el archivo aunque la escritura falle
    if archivo is not None:
        archivo.close()
```

### 3. Casos de prueba automáticos
`tests/test_simulation.py` contiene 8 secciones de prueba que demuestran
tanto operaciones válidas como inválidas, sin necesidad de la interfaz gráfica.

### 4. Documentación interna mejorada
Todos los módulos incluyen docstrings explicativos en clases y métodos
importantes, con descripción de parámetros, retornos y comportamiento esperado.
