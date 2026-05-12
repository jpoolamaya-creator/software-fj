# =============================================================================
# app.py — Interfaz gráfica principal de Software FJ (Tkinter)
# =============================================================================
# Punto de entrada de la aplicación. Importa todos los módulos del dominio
# y construye la ventana principal con sidebar de navegación.
#
# Para ejecutar:
#     cd software_fj && python app.py
# =============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import date, timedelta

from management import ManagementSystem
from services import (
    RoomReservationService, EquipmentRentalService, SpecializedConsultingService
)
from reservations import ReservationStatus
from exceptions import SoftwareFJBaseError


# =============================================================================
# Paleta de colores y fuentes (tema oscuro Catppuccin Mocha)
# =============================================================================

COLORS = {
    "bg":        "#1E1E2E",   # Fondo principal oscuro
    "sidebar":   "#181825",   # Fondo de la barra lateral
    "card":      "#313244",   # Fondo de tarjetas y diálogos
    "accent":    "#CBA6F7",   # Morado - acento principal
    "accent2":   "#89B4FA",   # Azul - acento secundario
    "green":     "#A6E3A1",   # Verde - éxito / costos
    "red":       "#F38BA8",   # Rojo - error / cancelado
    "yellow":    "#F9E2AF",   # Amarillo - advertencia / pendiente
    "text":      "#CDD6F4",   # Texto principal
    "subtext":   "#BAC2DE",   # Texto secundario
    "border":    "#45475A",   # Bordes
    "pending":   "#F9E2AF",   # Color estado PENDIENTE
    "confirmed": "#89B4FA",   # Color estado CONFIRMADO
    "completed": "#A6E3A1",   # Color estado COMPLETADO
    "cancelled": "#F38BA8",   # Color estado CANCELADO
}

FONTS = {
    "title":   ("Segoe UI", 18, "bold"),
    "heading": ("Segoe UI", 13, "bold"),
    "body":    ("Segoe UI", 11),
    "small":   ("Segoe UI", 10),
    "mono":    ("Consolas", 10),
    "btn":     ("Segoe UI", 11, "bold"),
}


# =============================================================================
# APLICACIÓN PRINCIPAL
# =============================================================================

class SoftwareFJApp(tk.Tk):
    """
    Ventana principal de Software FJ.

    Construye la interfaz con:
        - Sidebar de navegación (Dashboard, Clientes, Servicios, Reservas, Log)
        - Área de contenido que muestra el frame activo
        - Datos de demostración precargados al iniciar

    Toda la lógica de negocio se delega al ManagementSystem; la GUI
    solo se encarga de presentación e interacción con el usuario.
    """

    def __init__(self) -> None:
        super().__init__()
        self.system = ManagementSystem()
        self.title("Software FJ – Sistema de Gestión Integrado")
        self.geometry("1200x750")
        self.minsize(1000, 650)
        self.configure(bg=COLORS["bg"])
        self._build_ui()
        self._load_demo_data()
        self._show_frame("dashboard")

    # =========================================================================
    # Construcción de la UI
    # =========================================================================

    def _build_ui(self) -> None:
        """Construye el sidebar y el área de contenido principal."""

        # ---- Sidebar --------------------------------------------------------
        self.sidebar = tk.Frame(self, bg=COLORS["sidebar"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Encabezado del sidebar con nombre y grupo
        tk.Label(self.sidebar, text="Software FJ",
                 bg=COLORS["sidebar"], fg=COLORS["accent"],
                 font=("Segoe UI", 16, "bold")).pack(pady=(24, 4))
        tk.Label(self.sidebar, text="UNAD · Grupo 371",
                 bg=COLORS["sidebar"], fg=COLORS["subtext"],
                 font=FONTS["small"]).pack(pady=(0, 24))

        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=16, pady=4)

        # Botones de navegación
        nav_items = [
            ("🏠  Dashboard",     "dashboard"),
            ("👤  Clientes",      "clients"),
            ("🛠️  Servicios",     "services"),
            ("📅  Reservas",      "reservations"),
            ("📋  Visor de Log",  "logs"),
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

        # ---- Área de contenido ----------------------------------------------
        self.content = tk.Frame(self, bg=COLORS["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        # Construye todos los frames (uno por sección)
        self._frames = {
            "dashboard":    self._build_dashboard(),
            "clients":      self._build_clients(),
            "services":     self._build_services(),
            "reservations": self._build_reservations(),
            "logs":         self._build_logs(),
        }

    def _show_frame(self, key: str) -> None:
        """Muestra el frame indicado y actualiza el resaltado del sidebar."""
        for frame in self._frames.values():
            frame.place_forget()
        self._frames[key].place(relx=0, rely=0, relwidth=1, relheight=1)

        # Actualiza el color del botón activo en el sidebar
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(bg=COLORS["card"], fg=COLORS["accent"])
            else:
                btn.configure(bg=COLORS["sidebar"], fg=COLORS["text"])

        # Refresca datos dinámicos al cambiar de sección
        refresh_map = {
            "dashboard":    self._refresh_dashboard,
            "clients":      self._refresh_clients_table,
            "services":     self._refresh_services_table,
            "reservations": self._refresh_reservations_table,
            "logs":         self._refresh_logs,
        }
        if key in refresh_map:
            refresh_map[key]()

    # =========================================================================
    # Dashboard
    # =========================================================================

    def _build_dashboard(self) -> tk.Frame:
        """Construye el frame del Dashboard con tarjetas de estadísticas."""
        frame = tk.Frame(self.content, bg=COLORS["bg"])

        tk.Label(frame, text="Dashboard", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(anchor="w", padx=30, pady=(24, 4))
        tk.Label(frame, text="Software FJ · Resumen del Sistema",
                 bg=COLORS["bg"], fg=COLORS["subtext"], font=FONTS["body"]).pack(anchor="w", padx=30, pady=(0, 20))

        # Fila de tarjetas de estadísticas
        self._stat_frame = tk.Frame(frame, bg=COLORS["bg"])
        self._stat_frame.pack(fill="x", padx=30)

        self._stat_labels = {}
        stats_def = [
            ("clientes",    "👤 Clientes",    COLORS["accent2"]),
            ("servicios",   "🛠 Servicios",   COLORS["accent"]),
            ("pendientes",  "⏳ Pendientes",  COLORS["pending"]),
            ("confirmadas", "✅ Confirmadas", COLORS["confirmed"]),
            ("completadas", "🏁 Completadas", COLORS["completed"]),
            ("canceladas",  "❌ Canceladas",  COLORS["cancelled"]),
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

        # Tabla de reservas recientes
        tk.Label(frame, text="Reservas Recientes", bg=COLORS["bg"],
                 fg=COLORS["text"], font=FONTS["heading"]).pack(anchor="w", padx=30, pady=(20, 6))

        cols = ("ID", "Cliente", "Servicio", "Fecha", "Horas", "Estado", "Costo")
        self._dash_tree = self._make_treeview(frame, cols, height=8)
        self._dash_tree.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        return frame

    def _refresh_dashboard(self) -> None:
        """Actualiza los contadores del dashboard y la tabla de reservas."""
        stats = self.system.get_stats()
        for key, lbl in self._stat_labels.items():
            lbl.configure(text=str(stats.get(key, 0)))

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

    # =========================================================================
    # Clientes
    # =========================================================================

    def _build_clients(self) -> tk.Frame:
        """Construye el frame de gestión de clientes."""
        frame = tk.Frame(self.content, bg=COLORS["bg"])

        hdr = tk.Frame(frame, bg=COLORS["bg"])
        hdr.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hdr, text="Clientes", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left")
        tk.Button(hdr, text="＋ Nuevo Cliente", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=6,
                  cursor="hand2", command=self._open_add_client).pack(side="right")

        cols = ("ID", "Nombre Completo", "Email", "Teléfono")
        self._clients_tree = self._make_treeview(frame, cols, height=12)
        self._clients_tree.pack(fill="both", expand=True, padx=30)

        btn_row = tk.Frame(frame, bg=COLORS["bg"])
        btn_row.pack(fill="x", padx=30, pady=10)
        tk.Button(btn_row, text="🗑 Eliminar Seleccionado", bg=COLORS["red"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=14, pady=6,
                  cursor="hand2", command=self._delete_client).pack(side="left", padx=(0, 8))

        return frame

    def _refresh_clients_table(self) -> None:
        """Recarga la tabla de clientes desde el sistema."""
        self._clients_tree.delete(*self._clients_tree.get_children())
        for c in self.system.list_clients():
            self._clients_tree.insert("", "end", values=(
                c.client_id, c.full_name, c.email, c.phone))

    def _open_add_client(self) -> None:
        """Abre el diálogo para registrar un nuevo cliente."""
        win = self._make_dialog("Registrar Nuevo Cliente", 420, 380)
        fields = {}
        labels = [
            ("ID del Cliente", "client_id"),
            ("Nombre",         "first_name"),
            ("Apellido",       "last_name"),
            ("Email",          "email"),
            ("Teléfono",       "phone"),
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
            """Valida y envía el formulario de registro."""
            try:
                cid = int(fields["client_id"].get())
            except ValueError:
                messagebox.showerror("Error", "El ID del cliente debe ser un número.", parent=win)
                return
            client, err = self.system.register_client(
                cid,
                fields["first_name"].get(),
                fields["last_name"].get(),
                fields["email"].get(),
                fields["phone"].get(),
            )
            if err:
                messagebox.showerror("Error de Validación", err, parent=win)
            else:
                messagebox.showinfo("Éxito", f"Cliente '{client.full_name}' registrado!", parent=win)
                win.destroy()
                self._refresh_clients_table()

        tk.Button(win, text="Registrar Cliente", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=8,
                  cursor="hand2", command=submit).grid(
            row=len(labels), column=0, columnspan=2, pady=16)

    def _delete_client(self) -> None:
        """Elimina el cliente seleccionado en la tabla."""
        sel = self._clients_tree.selection()
        if not sel:
            messagebox.showwarning("Sin Selección", "Selecciona un cliente para eliminar.")
            return
        vals = self._clients_tree.item(sel[0])["values"]
        cid, name = int(vals[0]), vals[1]
        if not messagebox.askyesno("Confirmar Eliminación", f"¿Eliminar al cliente '{name}' (ID {cid})?"):
            return
        ok, err = self.system.delete_client(cid)
        if err:
            messagebox.showerror("Error", err)
        else:
            messagebox.showinfo("Eliminado", f"Cliente #{cid} eliminado.")
            self._refresh_clients_table()

    # =========================================================================
    # Servicios
    # =========================================================================

    def _build_services(self) -> tk.Frame:
        """Construye el frame de gestión de servicios."""
        frame = tk.Frame(self.content, bg=COLORS["bg"])

        hdr = tk.Frame(frame, bg=COLORS["bg"])
        hdr.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hdr, text="Servicios", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left")
        tk.Button(hdr, text="＋ Nuevo Servicio", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=6,
                  cursor="hand2", command=self._open_add_service).pack(side="right")

        cols = ("Nombre", "Tipo", "Tarifa/h", "Detalles", "Disponible")
        self._services_tree = self._make_treeview(frame, cols, height=12)
        self._services_tree.pack(fill="both", expand=True, padx=30)

        btn_row = tk.Frame(frame, bg=COLORS["bg"])
        btn_row.pack(fill="x", padx=30, pady=10)
        tk.Button(btn_row, text="⏯ Cambiar Disponibilidad", bg=COLORS["yellow"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=14, pady=6,
                  cursor="hand2", command=self._toggle_service).pack(side="left")

        return frame

    def _refresh_services_table(self) -> None:
        """Recarga la tabla de servicios desde el sistema."""
        self._services_tree.delete(*self._services_tree.get_children())
        for svc in self.system.list_services():
            stype = svc.__class__.__name__.replace("Service", "")
            if isinstance(svc, RoomReservationService):
                details = f"Sala: {svc.room_name} | Cap: {svc.capacity}"
            elif isinstance(svc, EquipmentRentalService):
                details = f"Ítems: {len(svc.equipment_list)}"
            else:
                details = f"{svc.specialty} | {svc.expert_name}"
            self._services_tree.insert("", "end", values=(
                svc.name, stype, f"${svc.base_cost_per_hour:,.0f}",
                details, "Sí" if svc.available else "No",
            ), tags=("available" if svc.available else "unavailable",))
        self._services_tree.tag_configure("available",   foreground=COLORS["green"])
        self._services_tree.tag_configure("unavailable", foreground=COLORS["red"])

    def _open_add_service(self) -> None:
        """Abre el diálogo dinámico para agregar un nuevo servicio."""
        win = self._make_dialog("Agregar Nuevo Servicio", 460, 520)

        tk.Label(win, text="Tipo de Servicio", bg=COLORS["card"],
                 fg=COLORS["subtext"], font=FONTS["small"]).grid(row=0, column=0, sticky="w", padx=24, pady=8)
        stype_var = tk.StringVar(value="Reserva de Sala")
        stype_cb = ttk.Combobox(win, textvariable=stype_var, width=26, state="readonly",
                                values=["Reserva de Sala", "Alquiler de Equipo", "Consultoría"])
        stype_cb.grid(row=0, column=1, padx=24, pady=8)

        base_fields = [("Nombre del Servicio", "name"), ("Costo por Hora (COP)", "cost")]
        entries = {}

        for i, (lbl, key) in enumerate(base_fields, start=1):
            tk.Label(win, text=lbl, bg=COLORS["card"],
                     fg=COLORS["subtext"], font=FONTS["small"]).grid(row=i, column=0, sticky="w", padx=24, pady=8)
            e = tk.Entry(win, bg=COLORS["border"], fg=COLORS["text"],
                         insertbackground=COLORS["text"], font=FONTS["body"], relief="flat", width=28)
            e.grid(row=i, column=1, padx=24, pady=8)
            entries[key] = e

        # Campos adicionales dinámicos según el tipo de servicio
        extra_container = tk.Frame(win, bg=COLORS["card"])
        extra_container.grid(row=3, column=0, columnspan=2, sticky="ew", padx=24)

        def update_extras(*_):
            """Actualiza los campos adicionales según el tipo seleccionado."""
            for w in extra_container.winfo_children():
                w.destroy()
            for k in ["room_name", "capacity", "equipment", "specialty", "expert", "seniority"]:
                entries.pop(k, None)

            st = stype_var.get()
            if st == "Reserva de Sala":
                for r, (lbl, key) in enumerate([("Nombre de Sala", "room_name"), ("Capacidad", "capacity")]):
                    tk.Label(extra_container, text=lbl, bg=COLORS["card"],
                             fg=COLORS["subtext"], font=FONTS["small"]).grid(row=r, column=0, sticky="w", pady=6)
                    e = tk.Entry(extra_container, bg=COLORS["border"], fg=COLORS["text"],
                                 insertbackground=COLORS["text"], font=FONTS["body"], relief="flat", width=28)
                    e.grid(row=r, column=1, padx=8)
                    entries[key] = e
            elif st == "Alquiler de Equipo":
                tk.Label(extra_container, text="Equipos (separados por coma)",
                         bg=COLORS["card"], fg=COLORS["subtext"], font=FONTS["small"]).grid(
                    row=0, column=0, sticky="w", pady=6)
                e = tk.Entry(extra_container, bg=COLORS["border"], fg=COLORS["text"],
                             insertbackground=COLORS["text"], font=FONTS["body"], relief="flat", width=28)
                e.grid(row=0, column=1, padx=8)
                entries["equipment"] = e
            else:  # Consultoría
                for r, (lbl, key) in enumerate([("Especialidad", "specialty"),
                                                ("Nombre del Experto", "expert"),
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
            """Crea el servicio con los datos del formulario."""
            try:
                cost = float(entries["cost"].get())
            except ValueError:
                messagebox.showerror("Error", "El costo debe ser un número.", parent=win)
                return
            name = entries["name"].get().strip()
            st   = stype_var.get()
            try:
                if st == "Reserva de Sala":
                    try:
                        cap = int(entries["capacity"].get())
                    except ValueError:
                        messagebox.showerror("Error", "La capacidad debe ser un entero.", parent=win)
                        return
                    svc = RoomReservationService(name, cost, entries["room_name"].get(), cap)
                elif st == "Alquiler de Equipo":
                    items = [i.strip() for i in entries["equipment"].get().split(",") if i.strip()]
                    svc = EquipmentRentalService(name, cost, items)
                else:
                    sen = entries["seniority"].get()
                    svc = SpecializedConsultingService(
                        name, cost, entries["specialty"].get(), entries["expert"].get(), sen)
            except SoftwareFJBaseError as exc:
                messagebox.showerror("Error de Validación", str(exc), parent=win)
                return

            _, err = self.system.add_service(svc)
            if err:
                messagebox.showerror("Error", err, parent=win)
            else:
                messagebox.showinfo("Éxito", f"Servicio '{name}' agregado!", parent=win)
                win.destroy()
                self._refresh_services_table()

        tk.Button(win, text="Agregar Servicio", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=8,
                  cursor="hand2", command=submit).grid(row=10, column=0, columnspan=2, pady=16)

    def _toggle_service(self) -> None:
        """Cambia la disponibilidad del servicio seleccionado."""
        sel = self._services_tree.selection()
        if not sel:
            messagebox.showwarning("Sin Selección", "Por favor selecciona un servicio.")
            return
        name = self._services_tree.item(sel[0])["values"][0]
        ok, msg = self.system.toggle_service(name)
        (messagebox.showinfo if ok else messagebox.showerror)("Resultado", msg)
        self._refresh_services_table()

    # =========================================================================
    # Reservas
    # =========================================================================

    def _build_reservations(self) -> tk.Frame:
        """Construye el frame de gestión de reservas con filtros por estado."""
        frame = tk.Frame(self.content, bg=COLORS["bg"])

        hdr = tk.Frame(frame, bg=COLORS["bg"])
        hdr.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hdr, text="Reservas", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left")
        tk.Button(hdr, text="＋ Nueva Reserva", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=6,
                  cursor="hand2", command=self._open_add_reservation).pack(side="right")

        # Radio buttons de filtro por estado
        filter_row = tk.Frame(frame, bg=COLORS["bg"])
        filter_row.pack(fill="x", padx=30, pady=(0, 6))
        tk.Label(filter_row, text="Filtrar:", bg=COLORS["bg"],
                 fg=COLORS["subtext"], font=FONTS["small"]).pack(side="left")
        self._res_filter = tk.StringVar(value="ALL")
        for val in ["ALL", "PENDING", "CONFIRMED", "COMPLETED", "CANCELLED"]:
            tk.Radiobutton(filter_row, text=val, variable=self._res_filter,
                           value=val, bg=COLORS["bg"], fg=COLORS["text"],
                           selectcolor=COLORS["card"], activebackground=COLORS["bg"],
                           font=FONTS["small"],
                           command=self._refresh_reservations_table).pack(side="left", padx=8)

        cols = ("ID", "Cliente", "Servicio", "Fecha", "Horas", "Estado", "Costo")
        self._res_tree = self._make_treeview(frame, cols, height=10)
        self._res_tree.pack(fill="both", expand=True, padx=30)

        btn_row = tk.Frame(frame, bg=COLORS["bg"])
        btn_row.pack(fill="x", padx=30, pady=10)
        tk.Button(btn_row, text="✅ Confirmar",     bg=COLORS["confirmed"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._confirm_res).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="🏁 Completar",     bg=COLORS["completed"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._complete_res).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="❌ Cancelar",      bg=COLORS["red"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._cancel_res).pack(side="left", padx=(0, 6))
        tk.Button(btn_row, text="💰 Desglose de Costo", bg=COLORS["yellow"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=12, pady=6,
                  cursor="hand2", command=self._cost_details).pack(side="left")

        return frame

    def _refresh_reservations_table(self) -> None:
        """Recarga la tabla de reservas aplicando el filtro de estado activo."""
        self._res_tree.delete(*self._res_tree.get_children())
        filt      = self._res_filter.get()
        status_map = {s.value: s for s in ReservationStatus}
        sf        = status_map.get(filt)    # None si filt == "ALL"
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
        """Retorna el ID de la reserva seleccionada, o None si no hay selección."""
        sel = self._res_tree.selection()
        if not sel:
            messagebox.showwarning("Sin Selección", "Por favor selecciona una reserva.")
            return None
        return int(sel[0])

    def _confirm_res(self):
        rid = self._get_selected_res_id()
        if rid is None:
            return
        ok, msg = self.system.confirm_reservation(rid)
        (messagebox.showinfo if ok else messagebox.showerror)("Resultado", msg)
        self._refresh_reservations_table()

    def _complete_res(self):
        rid = self._get_selected_res_id()
        if rid is None:
            return
        ok, msg = self.system.complete_reservation(rid)
        (messagebox.showinfo if ok else messagebox.showerror)("Resultado", msg)
        self._refresh_reservations_table()

    def _cancel_res(self):
        rid = self._get_selected_res_id()
        if rid is None:
            return
        ok, msg = self.system.cancel_reservation(rid)
        (messagebox.showinfo if ok else messagebox.showerror)("Resultado", msg)
        self._refresh_reservations_table()

    def _cost_details(self):
        """Muestra un desglose del costo con distintos impuestos y descuentos."""
        rid = self._get_selected_res_id()
        if rid is None:
            return
        res = self.system._reservations.get(rid)
        if not res:
            return
        win = self._make_dialog("Desglose de Costo", 380, 300)
        tk.Label(win, text=f"Reserva #{rid} – {res.service.name}",
                 bg=COLORS["card"], fg=COLORS["accent"], font=FONTS["heading"]).pack(pady=(16, 8))

        rows = [
            ("IVA 19% (estándar)",    res.calculate_total()),
            ("IVA 5% (exento)",       res.calculate_total(tax_rate=0.05)),
            ("10% de descuento",      res.calculate_total(discount_pct=10)),
            ("20% desc. + IVA 5%",   res.calculate_total(tax_rate=0.05, discount_pct=20)),
        ]
        for label, cost in rows:
            row = tk.Frame(win, bg=COLORS["card"])
            row.pack(fill="x", padx=24, pady=4)
            tk.Label(row, text=label, bg=COLORS["card"],
                     fg=COLORS["subtext"], font=FONTS["small"]).pack(side="left")
            tk.Label(row, text=f"${cost:,.2f} COP", bg=COLORS["card"],
                     fg=COLORS["green"], font=FONTS["body"]).pack(side="right")

    def _open_add_reservation(self):
        """Abre el diálogo para crear una nueva reserva."""
        win = self._make_dialog("Nueva Reserva", 440, 420)

        clients  = self.system.list_clients()
        services = self.system.list_services()
        if not clients:
            messagebox.showwarning("Sin Clientes", "Registra al menos un cliente primero.", parent=win)
            win.destroy()
            return
        if not services:
            messagebox.showwarning("Sin Servicios", "Agrega al menos un servicio primero.", parent=win)
            win.destroy()
            return

        client_options  = [f"{c.client_id} – {c.full_name}" for c in clients]
        service_options = [s.name for s in services]

        fields_def = [
            ("Cliente",             "client",  "combo", client_options),
            ("Servicio",            "service", "combo", service_options),
            ("Fecha (AAAA-MM-DD)",  "date",    "entry", None),
            ("Duración (horas)",    "hours",   "entry", None),
            ("Notas",               "notes",   "entry", None),
        ]
        entries = {}
        for i, (lbl, key, wtype, opts) in enumerate(fields_def):
            tk.Label(win, text=lbl, bg=COLORS["card"],
                     fg=COLORS["subtext"], font=FONTS["small"]).grid(
                row=i, column=0, sticky="w", padx=24, pady=8)
            if wtype == "combo":
                var = tk.StringVar(value=opts[0])
                cb  = ttk.Combobox(win, textvariable=var, values=opts,
                                   state="readonly", width=27)
                cb.grid(row=i, column=1, padx=24, pady=8)
                entries[key] = var
            else:
                e = tk.Entry(win, bg=COLORS["border"], fg=COLORS["text"],
                             insertbackground=COLORS["text"], font=FONTS["body"],
                             relief="flat", width=29)
                if key == "date":
                    e.insert(0, str(date.today()))   # Fecha de hoy como valor por defecto
                e.grid(row=i, column=1, padx=24, pady=8)
                entries[key] = e

        def submit():
            """Valida y crea la reserva con los datos ingresados."""
            try:
                cid = int(entries["client"].get().split("–")[0].strip())
            except Exception:
                messagebox.showerror("Error", "Selecciona un cliente válido.", parent=win)
                return
            svc_name = entries["service"].get()
            date_str = entries["date"].get()
            try:
                res_date = date.fromisoformat(date_str)
            except ValueError:
                messagebox.showerror("Error", "La fecha debe tener formato AAAA-MM-DD.", parent=win)
                return
            try:
                hours = float(entries["hours"].get())
            except ValueError:
                messagebox.showerror("Error", "La duración debe ser un número.", parent=win)
                return
            notes = entries["notes"].get()

            res, err = self.system.create_reservation(cid, svc_name, res_date, hours, notes)
            if err:
                messagebox.showerror("Error", err, parent=win)
            else:
                cost = res.calculate_total()
                messagebox.showinfo("Éxito",
                    f"¡Reserva #{res.reservation_id} creada!\nTotal: ${cost:,.2f} COP", parent=win)
                win.destroy()
                self._refresh_reservations_table()

        tk.Button(win, text="Crear Reserva", bg=COLORS["accent"],
                  fg=COLORS["bg"], font=FONTS["btn"], bd=0, padx=16, pady=8,
                  cursor="hand2", command=submit).grid(
            row=len(fields_def), column=0, columnspan=2, pady=16)

    # =========================================================================
    # Log de eventos
    # =========================================================================

    def _build_logs(self) -> tk.Frame:
        """Construye el frame del visor de log de eventos."""
        frame = tk.Frame(self.content, bg=COLORS["bg"])

        hdr = tk.Frame(frame, bg=COLORS["bg"])
        hdr.pack(fill="x", padx=30, pady=(24, 10))
        tk.Label(hdr, text="Log de Eventos", bg=COLORS["bg"],
                 fg=COLORS["accent"], font=FONTS["title"]).pack(side="left")
        tk.Button(hdr, text="🔄 Actualizar", bg=COLORS["card"],
                  fg=COLORS["text"], font=FONTS["btn"], bd=0, padx=14, pady=6,
                  cursor="hand2", command=self._refresh_logs).pack(side="right")

        self._log_text = scrolledtext.ScrolledText(
            frame, bg=COLORS["card"], fg=COLORS["text"],
            font=FONTS["mono"], relief="flat", state="disabled")
        self._log_text.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        return frame

    def _refresh_logs(self) -> None:
        """Recarga el contenido del archivo de log en el visor."""
        content = self.system.get_log()
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.insert("end", content)
        self._log_text.configure(state="disabled")
        self._log_text.see("end")   # Desplaza hasta el final

    # =========================================================================
    # Utilidades compartidas
    # =========================================================================

    def _make_treeview(self, parent, columns, height=10) -> ttk.Treeview:
        """Crea y retorna un Treeview estilizado con scrollbar vertical."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=COLORS["card"], foreground=COLORS["text"],
                        fieldbackground=COLORS["card"], rowheight=28, font=FONTS["small"])
        style.configure("Treeview.Heading",
                        background=COLORS["border"], foreground=COLORS["accent"],
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
        """Aplica colores por estado a las filas del Treeview."""
        tree.tag_configure("pending",   foreground=COLORS["pending"])
        tree.tag_configure("confirmed", foreground=COLORS["confirmed"])
        tree.tag_configure("completed", foreground=COLORS["completed"])
        tree.tag_configure("cancelled", foreground=COLORS["cancelled"])

    def _make_dialog(self, title: str, w: int, h: int) -> tk.Toplevel:
        """Crea y retorna una ventana de diálogo modal centrada."""
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry(f"{w}x{h}")
        win.configure(bg=COLORS["card"])
        win.resizable(False, False)
        win.grab_set()   # Bloquea la ventana principal mientras el diálogo esté abierto
        return win

    # =========================================================================
    # Datos de demostración
    # =========================================================================

    def _load_demo_data(self) -> None:
        """
        Pre-carga clientes, servicios y reservas de ejemplo para facilitar
        la demostración del sistema sin necesidad de ingresar datos manualmente.
        """
        # Clientes de ejemplo
        self.system.register_client(101, "Andrés",  "Martínez", "andres@softwarefj.com", "+57 300 123 4567")
        self.system.register_client(102, "Laura",   "Gómez",    "laura@softwarefj.com",  "3101234567")
        self.system.register_client(103, "Carlos",  "Ruiz",     "carlos@empresa.co",     "+57 310 987 6543")

        # Servicios de ejemplo (uno de cada tipo)
        room   = RoomReservationService("Conference Room A", 80_000, "Sala Innovación", 12)
        equip  = EquipmentRentalService("Tech Pack Pro", 25_000, ["Laptop Dell", "Proyector", "HDMI Hub"])
        consult = SpecializedConsultingService(
            "Cybersecurity Advisory", 150_000, "Ciberseguridad", "Dra. Ana Fernández", "senior")
        for svc in [room, equip, consult]:
            self.system.add_service(svc)

        # Reservas de ejemplo
        today = date.today()
        self.system.create_reservation(101, "Conference Room A", today + timedelta(7), 3, "Planeación Q3")
        self.system.create_reservation(102, "Tech Pack Pro",     today + timedelta(7), 8, "Demo de producto")
        res3, _ = self.system.create_reservation(103, "Cybersecurity Advisory", today + timedelta(14), 2)
        if res3:
            # Pre-confirma la tercera reserva para mostrar distintos estados
            self.system.confirm_reservation(res3.reservation_id)


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    app = SoftwareFJApp()
    app.mainloop()
