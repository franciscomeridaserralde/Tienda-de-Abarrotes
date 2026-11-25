"""
Tienda de abarrotes - Inventario y punto de venta
Python 3 + Tkinter (interfaz) + SQLite (bases de datos)

Archivos que genera en la misma carpeta:
  abarrotes.db  -> productos e inventario
  ventas.db     -> historial de ventas (archivo aparte)
  admin.json    -> usuario y contraseña del administrador (contraseña cifrada)

Ejecutar:  python abarrotes.py
"""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import sys
import tkinter as tk
from collections import namedtuple
from datetime import datetime, timedelta
from tkinter import ttk, messagebox

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PRODUCTOS = os.path.join(BASE_DIR, "abarrotes.db")
DB_VENTAS = os.path.join(BASE_DIR, "ventas.db")
ADMIN_FILE = os.path.join(BASE_DIR, "admin.json")
STOCK_BAJO = 5

FUENTE = "Segoe UI" if sys.platform.startswith("win") else "Helvetica"

Color = namedtuple("Color", "base oscuro claro")
VERDE = Color("#2e7d32", "#1b5e20", "#e8f5e9")
AZUL = Color("#1565c0", "#0d47a1", "#e3f2fd")
NARANJA = Color("#ef6c00", "#e65100", "#fff3e0")
ROJO = Color("#c62828", "#8e0000", "#ffebee")
MORADO = Color("#6a1b9a", "#4a148c", "#f3e5f5")
OSCURO = Color("#37474f", "#263238", "#cfd8dc")
NEUTRO = Color("#eceff1", "#cfd8dc", "#ffffff")

BG = "#f4f6f8"
TARJETA = "#ffffff"
FILA_ALT = "#f6f8fa"
TEXTO = "#263238"
SUAVE = "#78909c"
BORDE = "#dfe5ea"


def f(tam=11, estilo=""):
    return (FUENTE, tam, estilo) if estilo else (FUENTE, tam)


def dinero(x):
    return f"${x:,.2f}"


def fecha_larga():
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    h = datetime.now()
    return f"{dias[h.weekday()].capitalize()} {h.day} de {meses[h.month - 1]} de {h.year}"


def centrar(win, ancho, alto):
    win.update_idletasks()
    x = max((win.winfo_screenwidth() - ancho) // 2, 0)
    y = max((win.winfo_screenheight() - alto) // 2 - 20, 0)
    win.geometry(f"{ancho}x{alto}+{x}+{y}")


def configurar_estilos(root):
    s = ttk.Style(root)
    try:
        s.theme_use("clam")
    except tk.TclError:
        pass
    s.configure("TEntry", padding=6)
    s.configure("Vertical.TScrollbar", troughcolor=BG, background="#cfd8dc", bordercolor=BG,
                arrowcolor=SUAVE)
    for nombre, c in (("Verde", VERDE), ("Azul", AZUL), ("Naranja", NARANJA)):
        s.configure(f"{nombre}.Treeview", font=f(11), rowheight=32, background=TARJETA,
                    fieldbackground=TARJETA, foreground=TEXTO, borderwidth=0)
        s.configure(f"{nombre}.Treeview.Heading", font=f(10, "bold"), background=c.base,
                    foreground="white", relief="flat", padding=8)
        s.map(f"{nombre}.Treeview", background=[("selected", c.base)], foreground=[("selected", "white")])
        s.map(f"{nombre}.Treeview.Heading", background=[("active", c.oscuro)])


def preparar_tabla(tabla, bajo=ROJO):
    tabla.tag_configure("par", background=TARJETA)
    tabla.tag_configure("impar", background=FILA_ALT)
    tabla.tag_configure("bajo", background=bajo.claro, foreground=bajo.base)
    tabla.tag_configure("agotado", background="#f1f1f1", foreground="#b0bec5")


def tag_fila(i):
    return "par" if i % 2 == 0 else "impar"


def tarjeta(parent, **kw):
    return tk.Frame(parent, bg=TARJETA, highlightbackground=BORDE, highlightthickness=1, **kw)


def pantalla_completa(win):
    try:
        win.attributes("-fullscreen", True)
    except tk.TclError:
        try:
            win.state("zoomed")
        except tk.TclError:
            win.geometry(f"{win.winfo_screenwidth()}x{win.winfo_screenheight()}+0+0")
    win.bind("<F11>", lambda _e: win.attributes("-fullscreen", not win.attributes("-fullscreen")))


def encabezado(parent, icono, titulo, subtitulo, color, volver=None, texto_volver="←  Volver al menú"):
    barra = tk.Frame(parent, bg=color.base)
    barra.pack(fill="x")
    if volver:
        Boton(barra, texto_volver, volver, Color(color.oscuro, color.base, color.claro),
              tam=11, pady=8).pack(side="right", padx=22, pady=14)
    tk.Label(barra, text=f"{icono}  {titulo}", bg=color.base, fg="white",
             font=f(20, "bold")).pack(anchor="w", padx=22, pady=(14, 0))
    tk.Label(barra, text=subtitulo, bg=color.base, fg=color.claro,
             font=f(10)).pack(anchor="w", padx=22, pady=(0, 14))
    return barra


def hacer_modal(win, parent):
    win.transient(parent)
    win.update_idletasks()
    try:
        win.wait_visibility()
        win.grab_set()
    except tk.TclError:
        pass
    win.focus_set()
    win.wait_window(win)


def _puntero_dentro(widget):
    try:
        x, y = widget.winfo_pointerxy()
        w = widget.winfo_containing(x, y)
    except (tk.TclError, KeyError):
        return False
    while w is not None:
        if w is widget:
            return True
        w = w.master
    return False


class Boton(tk.Label):

    def __init__(self, parent, texto, comando, color=VERDE, tam=12, padx=16, pady=8, fg="white", **kw):
        super().__init__(parent, text=texto, bg=color.base, fg=fg, font=f(tam, "bold"),
                         padx=padx, pady=pady, cursor="hand2", **kw)
        self.comando = comando
        self.color = color
        self.bind("<Enter>", lambda _e: self.config(bg=color.oscuro, fg="white" if fg == "white" else fg))
        self.bind("<Leave>", lambda _e: self.config(bg=color.base))
        self.bind("<ButtonRelease-1>", self._soltar)

    def _soltar(self, e):
        if 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.comando()


class TarjetaMenu(tk.Frame):

    def __init__(self, parent, icono, titulo, descripcion, color, comando):
        super().__init__(parent, bg=color.base, cursor="hand2")
        self.color = color
        self.comando = comando
        ic = tk.Label(self, text=icono, font=f(38), bg=color.base, fg="white")
        ic.pack(side="left", padx=(26, 14), pady=20)
        txt = tk.Frame(self, bg=color.base)
        txt.pack(side="left", fill="both", expand=True)
        t = tk.Label(txt, text=titulo, font=f(22, "bold"), bg=color.base, fg="white", anchor="w")
        t.pack(anchor="w", pady=(22, 0))
        d = tk.Label(txt, text=descripcion, font=f(11), bg=color.base, fg=color.claro, anchor="w")
        d.pack(anchor="w", pady=(0, 20))
        fl = tk.Label(self, text="›", font=f(34, "bold"), bg=color.base, fg=color.claro)
        fl.pack(side="right", padx=24)
        self.todos = [self, ic, txt, t, d, fl]
        for w in self.todos:
            w.bind("<Enter>", lambda _e: self._pintar(self.color.oscuro))
            w.bind("<Leave>", self._salir)
            w.bind("<Button-1>", lambda _e: self.comando())

    def _pintar(self, c):
        for w in self.todos:
            w.config(bg=c)

    def _salir(self, _e):
        if not _puntero_dentro(self):
            self._pintar(self.color.base)


class ScrollFrame(tk.Frame):

    def __init__(self, parent, bg=TARJETA):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=bg)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.canvas.bind("<Enter>", self._activar_rueda)
        self.canvas.bind("<Leave>", self._desactivar_rueda)

    def _activar_rueda(self, _e):
        self.canvas.bind_all("<MouseWheel>", self._rueda)
        self.canvas.bind_all("<Button-4>", self._rueda)
        self.canvas.bind_all("<Button-5>", self._rueda)

    def _desactivar_rueda(self, _e):
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.unbind_all(ev)

    def _rueda(self, e):
        arriba = getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0
        self.canvas.yview_scroll(-1 if arriba else 1, "units")

class Database:

    def __init__(self, path=DB_PRODUCTOS):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS productos (
                   id       INTEGER PRIMARY KEY AUTOINCREMENT,
                   codigo   TEXT UNIQUE,
                   nombre   TEXT NOT NULL,
                   precio   REAL NOT NULL DEFAULT 0,
                   cantidad INTEGER NOT NULL DEFAULT 0
               )"""
        )
        self.conn.commit()

    def listar(self, filtro=""):
        like = f"%{filtro}%"
        return self.conn.execute(
            "SELECT id, codigo, nombre, precio, cantidad FROM productos "
            "WHERE nombre LIKE ? OR codigo LIKE ? ORDER BY nombre",
            (like, like),
        ).fetchall()

    def resumen(self):
        n, bajo = self.conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(cantidad <= ?), 0) FROM productos", (STOCK_BAJO,)
        ).fetchone()
        return n, int(bajo)

    def obtener(self, id_):
        return self.conn.execute(
            "SELECT id, codigo, nombre, precio, cantidad FROM productos WHERE id=?", (id_,)
        ).fetchone()

    def buscar_por_codigo(self, codigo):
        return self.conn.execute(
            "SELECT id, codigo, nombre, precio, cantidad FROM productos WHERE codigo=?", (codigo,)
        ).fetchone()

    def agregar(self, codigo, nombre, precio, cantidad):
        self.conn.execute(
            "INSERT INTO productos (codigo, nombre, precio, cantidad) VALUES (?,?,?,?)",
            (codigo or None, nombre, precio, cantidad),
        )
        self.conn.commit()

    def actualizar(self, id_, codigo, nombre, precio, cantidad):
        self.conn.execute(
            "UPDATE productos SET codigo=?, nombre=?, precio=?, cantidad=? WHERE id=?",
            (codigo or None, nombre, precio, cantidad, id_),
        )
        self.conn.commit()

    def ajustar_cantidad(self, id_, delta):
        self.conn.execute(
            "UPDATE productos SET cantidad = MAX(0, cantidad + ?) WHERE id=?", (delta, id_)
        )
        self.conn.commit()

    def eliminar(self, id_):
        self.conn.execute("DELETE FROM productos WHERE id=?", (id_,))
        self.conn.commit()


class VentasDB:

    def __init__(self, path=DB_VENTAS):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ventas (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha  TEXT NOT NULL,      -- AAAA-MM-DD
                hora   TEXT NOT NULL,      -- HH:MM:SS
                total  REAL NOT NULL,
                pago   REAL NOT NULL,
                cambio REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS detalle_venta (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id    INTEGER NOT NULL REFERENCES ventas(id),
                producto_id INTEGER,
                nombre      TEXT NOT NULL,
                precio      REAL NOT NULL,
                cantidad    INTEGER NOT NULL,
                subtotal    REAL NOT NULL
            );
            """
        )
        self.conn.commit()

    def registrar(self, items, total, pago):
        ahora = datetime.now()
        cur = self.conn.execute(
            "INSERT INTO ventas (fecha, hora, total, pago, cambio) VALUES (?,?,?,?,?)",
            (ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"), total, pago, pago - total),
        )
        venta_id = cur.lastrowid
        self.conn.executemany(
            "INSERT INTO detalle_venta (venta_id, producto_id, nombre, precio, cantidad, subtotal) "
            "VALUES (?,?,?,?,?,?)",
            [(venta_id, pid, nom, pre, cant, pre * cant) for pid, nom, pre, cant in items],
        )
        self.conn.commit()
        return venta_id

    def ventas_del_dia(self, fecha):
        return self.conn.execute(
            "SELECT id, hora, total, pago, cambio FROM ventas WHERE fecha=? ORDER BY id", (fecha,)
        ).fetchall()

    def detalle(self, venta_id):
        return self.conn.execute(
            "SELECT nombre, precio, cantidad, subtotal FROM detalle_venta WHERE venta_id=?", (venta_id,)
        ).fetchall()


class Auth:

    def __init__(self, path=ADMIN_FILE):
        self.path = path

    @staticmethod
    def _hash(password, salt):
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000).hex()

    def existe(self):
        return os.path.exists(self.path)

    def crear(self, usuario, password):
        salt = secrets.token_bytes(16)
        datos = {"usuario": usuario, "salt": salt.hex(), "hash": self._hash(password, salt)}
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(datos, fh)

    def validar(self, usuario, password):
        try:
            with open(self.path, encoding="utf-8") as fh:
                datos = json.load(fh)
            esperado = datos["hash"]
            salt = bytes.fromhex(datos["salt"])
            usuario_ok = hmac.compare_digest(usuario, datos["usuario"])
        except (OSError, KeyError, ValueError):
            return False
        pass_ok = hmac.compare_digest(self._hash(password, salt), esperado)
        return usuario_ok and pass_ok


class CredencialesDialog(tk.Toplevel):

    def __init__(self, parent, titulo, confirmar=False, mensaje=""):
        super().__init__(parent, bg=TARJETA)
        self.title(titulo)
        self.resultado = None
        self.confirmar = confirmar
        self.resizable(False, False)
        alto = 460 if confirmar else 400
        centrar(self, 400, alto)

        encabezado(self, "🔒", titulo, "Zona protegida", NARANJA)
        cuerpo = tk.Frame(self, bg=TARJETA)
        cuerpo.pack(fill="both", expand=True, padx=26, pady=16)
        if mensaje:
            tk.Label(cuerpo, text=mensaje, wraplength=340, justify="left", bg=TARJETA, fg=SUAVE,
                     font=f(10)).pack(anchor="w", pady=(0, 8))

        self.var_u, self.var_p, self.var_p2 = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self.ent_u = self._campo(cuerpo, "Usuario", self.var_u)
        self._campo(cuerpo, "Contraseña", self.var_p, oculto=True)
        if confirmar:
            self._campo(cuerpo, "Repetir contraseña", self.var_p2, oculto=True)

        self.lbl_error = tk.Label(cuerpo, text="", bg=TARJETA, fg=ROJO.base, font=f(10))
        self.lbl_error.pack(anchor="w", pady=(6, 0))

        botones = tk.Frame(cuerpo, bg=TARJETA)
        botones.pack(fill="x", pady=(8, 0))
        Boton(botones, "Aceptar", self.aceptar, NARANJA).pack(side="left", fill="x", expand=True, padx=(0, 6))
        Boton(botones, "Cancelar", self.destroy, NEUTRO, fg=TEXTO).pack(side="left", fill="x", expand=True)

        self.bind("<Return>", lambda _e: self.aceptar())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.ent_u.focus_set()
        hacer_modal(self, parent)

    @staticmethod
    def _campo(padre, texto, var, oculto=False):
        tk.Label(padre, text=texto, bg=TARJETA, fg=SUAVE, font=f(9)).pack(anchor="w", pady=(6, 0))
        e = ttk.Entry(padre, textvariable=var, font=f(12), show="•" if oculto else "")
        e.pack(fill="x")
        return e

    def aceptar(self):
        u, p = self.var_u.get().strip(), self.var_p.get()
        if not u or not p:
            self.lbl_error.config(text="Escribe usuario y contraseña.")
            return
        if self.confirmar:
            if len(p) < 4:
                self.lbl_error.config(text="La contraseña debe tener al menos 4 caracteres.")
                return
            if p != self.var_p2.get():
                self.lbl_error.config(text="Las contraseñas no coinciden.")
                return
        self.resultado = (u, p)
        self.destroy()


class CobroDialog(tk.Toplevel):

    def __init__(self, parent, total):
        super().__init__(parent, bg=TARJETA)
        self.title("Cobrar")
        self.total = total
        self.pago = None
        self.resizable(False, False)
        centrar(self, 460, 590)

        encabezado(self, "💵", "Cobrar", "Cuánto paga el cliente", VERDE)
        cuerpo = tk.Frame(self, bg=TARJETA)
        cuerpo.pack(fill="both", expand=True, padx=26, pady=14)

        tk.Label(cuerpo, text="TOTAL A PAGAR", bg=TARJETA, fg=SUAVE, font=f(10, "bold")).pack()
        tk.Label(cuerpo, text=dinero(total), bg=TARJETA, fg=VERDE.base, font=f(34, "bold")).pack(pady=(0, 10))

        tk.Label(cuerpo, text="El cliente paga con:", bg=TARJETA, fg=SUAVE, font=f(10)).pack(anchor="w")
        self.var = tk.StringVar(value=f"{total:.2f}")
        self.var.trace_add("write", lambda *_: self.actualizar())
        self.ent = ttk.Entry(cuerpo, textvariable=self.var, font=f(22, "bold"), justify="center")
        self.ent.pack(fill="x", pady=(2, 10))

        rapidos = tk.Frame(cuerpo, bg=TARJETA)
        rapidos.pack(fill="x")
        montos = [("Exacto", None), ("$20", 20), ("$50", 50), ("$100", 100),
                  ("$200", 200), ("$500", 500), ("$1000", 1000)]
        for i, (texto, monto) in enumerate(montos):
            Boton(rapidos, texto, lambda m=monto: self.poner(m), AZUL, tam=11, padx=6, pady=6).grid(
                row=i // 4, column=i % 4, sticky="ew", padx=3, pady=3)
        for c in range(4):
            rapidos.columnconfigure(c, weight=1)

        self.caja = tk.Frame(cuerpo, bg=VERDE.claro)
        self.caja.pack(fill="x", pady=14)
        self.lbl_cambio = tk.Label(self.caja, text="", bg=VERDE.claro, fg=VERDE.base, font=f(20, "bold"), pady=12)
        self.lbl_cambio.pack(fill="x")

        botones = tk.Frame(cuerpo, bg=TARJETA)
        botones.pack(fill="x")
        Boton(botones, "✔  Confirmar cobro", self.confirmar, VERDE, tam=13, pady=10).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        Boton(botones, "Cancelar", self.destroy, NEUTRO, fg=TEXTO, tam=13, pady=10).pack(side="left")

        self.bind("<Return>", lambda _e: self.confirmar())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.actualizar()
        self.ent.focus_set()
        self.ent.select_range(0, "end")
        hacer_modal(self, parent)

    def _valor(self):
        try:
            return float(self.var.get().replace(",", "").replace("$", "") or 0)
        except ValueError:
            return 0.0

    def poner(self, monto):
        self.var.set(f"{self.total:.2f}" if monto is None else f"{monto:.2f}")

    def actualizar(self):
        v = self._valor()
        if v + 0.001 >= self.total:
            c = VERDE
            texto = f"Cambio: {dinero(v - self.total)}"
        else:
            c = ROJO
            texto = f"Faltan {dinero(self.total - v)}"
        self.caja.config(bg=c.claro)
        self.lbl_cambio.config(text=texto, bg=c.claro, fg=c.base)

    def confirmar(self):
        v = self._valor()
        if v + 0.001 < self.total:
            self.lbl_cambio.config(text=f"Faltan {dinero(self.total - v)}")
            return
        self.pago = v
        self.destroy()


class ExitoDialog(tk.Toplevel):

    def __init__(self, parent, total, pago):
        super().__init__(parent, bg=TARJETA)
        self.title("Venta registrada")
        self.resizable(False, False)
        centrar(self, 400, 430)

        franja = tk.Frame(self, bg=VERDE.base)
        franja.pack(fill="x")
        tk.Label(franja, text="✔", bg=VERDE.base, fg="white", font=f(48, "bold")).pack(pady=(14, 0))
        tk.Label(franja, text="Venta registrada", bg=VERDE.base, fg="white",
                 font=f(16, "bold")).pack(pady=(0, 16))

        cuerpo = tk.Frame(self, bg=TARJETA)
        cuerpo.pack(fill="both", expand=True, padx=30, pady=16)
        for texto, valor in (("Total", dinero(total)), ("Pagó con", dinero(pago))):
            fila = tk.Frame(cuerpo, bg=TARJETA)
            fila.pack(fill="x", pady=2)
            tk.Label(fila, text=texto, bg=TARJETA, fg=SUAVE, font=f(12)).pack(side="left")
            tk.Label(fila, text=valor, bg=TARJETA, fg=TEXTO, font=f(12, "bold")).pack(side="right")

        caja = tk.Frame(cuerpo, bg=VERDE.claro)
        caja.pack(fill="x", pady=14)
        tk.Label(caja, text="ENTREGAR CAMBIO", bg=VERDE.claro, fg=VERDE.base, font=f(10, "bold")).pack(pady=(10, 0))
        tk.Label(caja, text=dinero(pago - total), bg=VERDE.claro, fg=VERDE.base,
                 font=f(30, "bold")).pack(pady=(0, 10))

        Boton(cuerpo, "Nueva venta", self.destroy, VERDE, tam=13, pady=10).pack(fill="x")
        self.bind("<Return>", lambda _e: self.destroy())
        self.bind("<Escape>", lambda _e: self.destroy())
        hacer_modal(self, parent)


class VentaWindow(tk.Toplevel):
    def __init__(self, parent, db, ventas):
        super().__init__(parent, bg=BG)
        self.title("Venta")
        pantalla_completa(self)
        self.db = db
        self.ventas = ventas
        self.carrito = {}

        encabezado(self, "🛒", "Venta", "Busca o escanea los productos y agrégalos al carrito", VERDE,
                   volver=self.destroy)
        cuerpo = tk.Frame(self, bg=BG)
        cuerpo.pack(fill="both", expand=True, padx=14, pady=14)
        cuerpo.columnconfigure(0, weight=5, uniform="col")
        cuerpo.columnconfigure(1, weight=6, uniform="col")
        cuerpo.rowconfigure(0, weight=1)

        izq = tarjeta(cuerpo)
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        der = tarjeta(cuerpo)
        der.grid(row=0, column=1, sticky="nsew", padx=(7, 0))

        self._panel_productos(izq)
        self._panel_carrito(der)
        self.refrescar_productos()
        self.render_carrito()
        self.ent_buscar.focus_set()

    def _panel_productos(self, marco):
        tk.Label(marco, text="Productos", bg=TARJETA, fg=VERDE.base, font=f(14, "bold")).pack(
            anchor="w", padx=14, pady=(12, 0))
        tk.Label(marco, text="Escribe el nombre o escanea el código y presiona Enter", bg=TARJETA,
                 fg=SUAVE, font=f(9)).pack(anchor="w", padx=14, pady=(0, 6))

        self.var_buscar = tk.StringVar()
        self.var_buscar.trace_add("write", lambda *_: self.refrescar_productos())
        self.ent_buscar = ttk.Entry(marco, textvariable=self.var_buscar, font=f(13))
        self.ent_buscar.pack(fill="x", padx=14, pady=(0, 10))
        self.ent_buscar.bind("<Return>", self._enter_buscar)

        cuerpo = tk.Frame(marco, bg=TARJETA)
        cuerpo.pack(fill="both", expand=True, padx=14)
        self.lista = ttk.Treeview(cuerpo, columns=("nombre", "precio", "stock"), show="headings",
                                  selectmode="browse", style="Verde.Treeview")
        for col, texto, ancho, ancla in [("nombre", "Producto", 230, "w"), ("precio", "Precio", 90, "e"),
                                         ("stock", "Existencia", 90, "center")]:
            self.lista.heading(col, text=texto)
            self.lista.column(col, width=ancho, anchor=ancla)
        preparar_tabla(self.lista, bajo=NARANJA)
        sb = ttk.Scrollbar(cuerpo, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=sb.set)
        self.lista.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.lista.bind("<Double-1>", lambda _e: self.agregar_seleccionado())

        Boton(marco, "Agregar al carrito  →", self.agregar_seleccionado, VERDE, tam=13, pady=10).pack(
            fill="x", padx=14, pady=(10, 4))
        tk.Label(marco, text="Naranja = quedan pocas piezas   ·   Gris = agotado", bg=TARJETA,
                 fg=SUAVE, font=f(9)).pack(pady=(0, 10))

        self.bind("<FocusIn>", lambda e: self.refrescar_productos() if e.widget is self else None)

    def _panel_carrito(self, marco):
        enc = tk.Frame(marco, bg=TARJETA)
        enc.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(enc, text="🛒 Carrito", bg=TARJETA, fg=VERDE.base, font=f(14, "bold")).pack(side="left")
        self.lbl_items = tk.Label(enc, text="", bg=TARJETA, fg=SUAVE, font=f(10))
        self.lbl_items.pack(side="right")
        tk.Frame(marco, bg=BORDE, height=1).pack(fill="x", padx=14)

        self.scroll = ScrollFrame(marco)
        self.scroll.pack(fill="both", expand=True, padx=14, pady=6)

        total = tk.Frame(marco, bg=VERDE.claro)
        total.pack(fill="x", padx=14, pady=(4, 10))
        tk.Label(total, text="TOTAL", bg=VERDE.claro, fg=VERDE.base, font=f(11, "bold")).pack(
            side="left", padx=16, pady=12)
        self.lbl_total = tk.Label(total, text="$0.00", bg=VERDE.claro, fg=VERDE.base, font=f(28, "bold"))
        self.lbl_total.pack(side="right", padx=16)

        botones = tk.Frame(marco, bg=TARJETA)
        botones.pack(fill="x", padx=14, pady=(0, 14))
        Boton(botones, "COBRAR", self.cobrar, VERDE, tam=17, pady=12).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        Boton(botones, "Vaciar", self.vaciar, ROJO, tam=12, pady=14).pack(side="left", padx=3)
        Boton(botones, "Cerrar", self.destroy, NEUTRO, fg=TEXTO, tam=12, pady=14).pack(side="left", padx=(3, 0))

    def refrescar_productos(self):
        if not self.winfo_exists():
            return
        sel = self.lista.selection()
        self.lista.delete(*self.lista.get_children())
        for i, (id_, _codigo, nombre, precio, cantidad) in enumerate(self.db.listar(self.var_buscar.get().strip())):
            if cantidad <= 0:
                tag = "agotado"
            elif cantidad <= STOCK_BAJO:
                tag = "bajo"
            else:
                tag = tag_fila(i)
            self.lista.insert("", "end", iid=str(id_), values=(nombre, dinero(precio), cantidad), tags=(tag,))
        if sel and self.lista.exists(sel[0]):
            self.lista.selection_set(sel[0])

    def _enter_buscar(self, _e):
        texto = self.var_buscar.get().strip()
        if not texto:
            return
        prod = self.db.buscar_por_codigo(texto)
        if prod:
            self.agregar_al_carrito(prod[0])
            self.var_buscar.set("")
            return
        hijos = self.lista.get_children()
        if len(hijos) == 1:
            self.agregar_al_carrito(int(hijos[0]))
            self.var_buscar.set("")
        elif not hijos:
            messagebox.showinfo("Sin resultados", "No se encontró ningún producto.", parent=self)

    def agregar_seleccionado(self):
        sel = self.lista.selection()
        if sel:
            self.agregar_al_carrito(int(sel[0]))
        else:
            messagebox.showinfo("Elige un producto", "Selecciona un producto de la lista.", parent=self)

    def agregar_al_carrito(self, pid):
        prod = self.db.obtener(pid)
        if not prod:
            return
        _id, _codigo, nombre, precio, stock = prod
        actual = self.carrito.get(pid, {}).get("cantidad", 0)
        if actual + 1 > stock:
            messagebox.showwarning("Sin existencias", f"Solo hay {stock} pieza(s) de {nombre}.", parent=self)
            return
        if pid in self.carrito:
            self.carrito[pid]["cantidad"] += 1
        else:
            self.carrito[pid] = {"nombre": nombre, "precio": precio, "cantidad": 1}
        self.render_carrito()

    def cambiar_cantidad(self, pid, delta):
        item = self.carrito.get(pid)
        if not item:
            return
        nueva = item["cantidad"] + delta
        if nueva <= 0:
            del self.carrito[pid]
        else:
            if delta > 0:
                prod = self.db.obtener(pid)
                if not prod or nueva > prod[4]:
                    messagebox.showwarning("Sin existencias",
                                           f"Solo hay {prod[4] if prod else 0} pieza(s) de {item['nombre']}.",
                                           parent=self)
                    return
            item["cantidad"] = nueva
        self.render_carrito()

    def quitar(self, pid):
        self.carrito.pop(pid, None)
        self.render_carrito()

    def vaciar(self):
        if self.carrito and messagebox.askyesno("Vaciar", "¿Quitar todo del carrito?", parent=self):
            self.carrito.clear()
            self.render_carrito()

    def total(self):
        return sum(i["precio"] * i["cantidad"] for i in self.carrito.values())

    def render_carrito(self):
        inner = self.scroll.inner
        for w in inner.winfo_children():
            w.destroy()

        if not self.carrito:
            tk.Label(inner, text="🛒\n\nTu carrito está vacío\nAgrega productos desde la lista",
                     font=f(13), fg=SUAVE, bg=TARJETA, pady=70).pack(fill="x")

        for i, (pid, it) in enumerate(self.carrito.items()):
            bg = TARJETA if i % 2 == 0 else FILA_ALT
            fila = tk.Frame(inner, bg=bg)
            fila.pack(fill="x")
            Boton(fila, "✕", lambda p=pid: self.quitar(p), NEUTRO, fg=ROJO.base, tam=11, padx=8, pady=3).pack(
                side="right", padx=(8, 8), pady=8)
            tk.Label(fila, text=dinero(it["precio"] * it["cantidad"]), width=10, anchor="e", bg=bg,
                     fg=TEXTO, font=f(12, "bold")).pack(side="right")
            Boton(fila, "+", lambda p=pid: self.cambiar_cantidad(p, +1), VERDE, tam=14, padx=10, pady=1).pack(
                side="right", padx=(0, 6))
            tk.Label(fila, text=str(it["cantidad"]), width=3, anchor="center", bg=bg, fg=TEXTO,
                     font=f(14, "bold")).pack(side="right")
            Boton(fila, "−", lambda p=pid: self.cambiar_cantidad(p, -1), ROJO, tam=14, padx=10, pady=1).pack(
                side="right", padx=(10, 0))
            tk.Label(fila, text=f"{it['nombre']}\n{dinero(it['precio'])} c/u", justify="left", anchor="w",
                     bg=bg, fg=TEXTO, font=f(11), wraplength=200).pack(side="left", fill="x", expand=True,
                                                                       padx=10, pady=6)

        piezas = sum(i["cantidad"] for i in self.carrito.values())
        self.lbl_items.config(text=f"{piezas} pieza(s)" if piezas else "")
        self.lbl_total.config(text=dinero(self.total()))

    def cobrar(self):
        if not self.carrito:
            messagebox.showinfo("Carrito vacío", "Agrega productos antes de cobrar.", parent=self)
            return
        total = self.total()

        for pid, it in self.carrito.items():
            prod = self.db.obtener(pid)
            if not prod or prod[4] < it["cantidad"]:
                messagebox.showerror("Sin existencias",
                                     f"Ya no hay suficiente de {it['nombre']}. Ajusta el carrito.", parent=self)
                return

        dlg = CobroDialog(self, total)
        if dlg.pago is None:
            return
        pago = dlg.pago

        items = [(pid, it["nombre"], it["precio"], it["cantidad"]) for pid, it in self.carrito.items()]
        self.ventas.registrar(items, total, pago)
        for pid, _n, _p, cant in items:
            self.db.ajustar_cantidad(pid, -cant)

        self.carrito.clear()
        self.render_carrito()
        self.refrescar_productos()
        ExitoDialog(self, total, pago)
        self.ent_buscar.focus_set()


class ProductosWindow(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent, bg=BG)
        self.title("Agregar productos")
        pantalla_completa(self)
        self.db = db
        self.seleccion_id = None

        encabezado(self, "📦", "Productos", "Registra productos nuevos, cambia precios y surte el inventario", AZUL,
                   volver=self.destroy)
        cuerpo = tk.Frame(self, bg=BG)
        cuerpo.pack(fill="both", expand=True, padx=14, pady=14)

        self._crear_formulario(cuerpo)
        self._crear_busqueda(cuerpo)
        self._crear_tabla(cuerpo)
        self.refrescar()
        self.ent_codigo.focus_set()

    def _crear_formulario(self, padre):
        form = tarjeta(padre)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        self.lbl_modo = tk.Label(form, text="＋ Nuevo producto", bg=TARJETA, fg=AZUL.base, font=f(14, "bold"))
        self.lbl_modo.grid(row=0, column=0, columnspan=4, sticky="w", padx=14, pady=(12, 6))

        self.var_codigo, self.var_nombre = tk.StringVar(), tk.StringVar()
        self.var_precio, self.var_cantidad = tk.StringVar(), tk.StringVar()
        campos = [("Código de barras (opcional)", self.var_codigo, 18),
                  ("Nombre del producto *", self.var_nombre, 30),
                  ("Precio ($)", self.var_precio, 10),
                  ("Cantidad en existencia", self.var_cantidad, 12)]
        entradas = []
        for i, (texto, var, ancho) in enumerate(campos):
            tk.Label(form, text=texto, bg=TARJETA, fg=SUAVE, font=f(9)).grid(
                row=1, column=i, sticky="w", padx=(14 if i == 0 else 6, 6))
            e = ttk.Entry(form, textvariable=var, width=ancho, font=f(12))
            e.grid(row=2, column=i, sticky="ew", padx=(14 if i == 0 else 6, 6), pady=(0, 12))
            e.bind("<Return>", self.enter)
            entradas.append(e)
        self.ent_codigo = entradas[0]

        botones = tk.Frame(form, bg=TARJETA)
        botones.grid(row=3, column=0, columnspan=4, sticky="w", padx=14, pady=(0, 14))
        Boton(botones, "＋  Agregar", self.agregar, VERDE, tam=11).pack(side="left", padx=(0, 6))
        Boton(botones, "💾  Guardar cambios", self.guardar_cambios, AZUL, tam=11).pack(side="left", padx=6)
        Boton(botones, "📥  Surtir (entrada)", self.surtir, NARANJA, tam=11).pack(side="left", padx=6)
        Boton(botones, "🗑  Eliminar", self.eliminar, ROJO, tam=11).pack(side="left", padx=6)
        Boton(botones, "Limpiar", self.limpiar, NEUTRO, fg=TEXTO, tam=11).pack(side="left", padx=6)

    def _crear_busqueda(self, padre):
        barra = tk.Frame(padre, bg=BG)
        barra.pack(fill="x", pady=(12, 8))
        tk.Label(barra, text="🔍 Buscar:", bg=BG, fg=TEXTO, font=f(11, "bold")).pack(side="left")
        self.var_buscar = tk.StringVar()
        self.var_buscar.trace_add("write", lambda *_: self.refrescar())
        ttk.Entry(barra, textvariable=self.var_buscar, width=28, font=f(12)).pack(side="left", padx=8)

        self.lbl_bajo = tk.Label(barra, text="", bg=ROJO.claro, fg=ROJO.base, font=f(10, "bold"), padx=10, pady=4)
        self.lbl_bajo.pack(side="right", padx=(8, 0))
        self.lbl_valor = tk.Label(barra, text="", bg=VERDE.claro, fg=VERDE.base, font=f(10, "bold"), padx=10, pady=4)
        self.lbl_valor.pack(side="right", padx=8)
        self.lbl_n = tk.Label(barra, text="", bg=AZUL.claro, fg=AZUL.base, font=f(10, "bold"), padx=10, pady=4)
        self.lbl_n.pack(side="right")

    def _crear_tabla(self, padre):
        marco = tarjeta(padre)
        marco.pack(fill="both", expand=True)
        cols = ("codigo", "nombre", "precio", "cantidad")
        self.tabla = ttk.Treeview(marco, columns=cols, show="headings", selectmode="browse",
                                  style="Azul.Treeview")
        for col, texto, ancho, ancla in [("codigo", "Código", 130, "w"), ("nombre", "Nombre", 360, "w"),
                                         ("precio", "Precio", 100, "e"), ("cantidad", "Cantidad", 100, "center")]:
            self.tabla.heading(col, text=texto)
            self.tabla.column(col, width=ancho, anchor=ancla)
        preparar_tabla(self.tabla, bajo=ROJO)
        sb = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=sb.set)
        self.tabla.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        sb.pack(side="right", fill="y")
        self.tabla.bind("<<TreeviewSelect>>", self.al_seleccionar)
        tk.Label(padre, text=f"Rojo = quedan {STOCK_BAJO} piezas o menos   ·   Selecciona un producto para editarlo",
                 bg=BG, fg=SUAVE, font=f(9)).pack(anchor="w", pady=(6, 0))

    def enter(self, _e=None):
        if self.seleccion_id is not None:
            self.guardar_cambios()
        else:
            self.agregar()

    def refrescar(self):
        self.tabla.delete(*self.tabla.get_children())
        filas = self.db.listar(self.var_buscar.get().strip())
        for i, (id_, codigo, nombre, precio, cantidad) in enumerate(filas):
            tag = "bajo" if cantidad <= STOCK_BAJO else tag_fila(i)
            self.tabla.insert("", "end", iid=str(id_),
                              values=(codigo or "", nombre, dinero(precio), cantidad), tags=(tag,))
        total = sum(r[3] * r[4] for r in filas)
        bajos = sum(1 for r in filas if r[4] <= STOCK_BAJO)
        self.lbl_n.config(text=f"{len(filas)} productos")
        self.lbl_valor.config(text=f"Inventario: {dinero(total)}")
        self.lbl_bajo.config(text=f"⚠ {bajos} con poco stock")

    def leer_formulario(self):
        nombre = self.var_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Falta información", "El nombre es obligatorio.", parent=self)
            return None
        try:
            precio = float(self.var_precio.get() or 0)
            cantidad = int(self.var_cantidad.get() or 0)
            if precio < 0 or cantidad < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Dato inválido", "Precio y cantidad deben ser números positivos.", parent=self)
            return None
        return self.var_codigo.get().strip(), nombre, precio, cantidad

    def agregar(self):
        datos = self.leer_formulario()
        if not datos:
            return
        try:
            self.db.agregar(*datos)
        except sqlite3.IntegrityError:
            messagebox.showerror("Código repetido", "Ya existe un producto con ese código.", parent=self)
            return
        self.limpiar()
        self.refrescar()
        self.ent_codigo.focus_set()

    def guardar_cambios(self):
        if self.seleccion_id is None:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la tabla primero.", parent=self)
            return
        datos = self.leer_formulario()
        if not datos:
            return
        try:
            self.db.actualizar(self.seleccion_id, *datos)
        except sqlite3.IntegrityError:
            messagebox.showerror("Código repetido", "Ya existe un producto con ese código.", parent=self)
            return
        self.refrescar()

    def eliminar(self):
        if self.seleccion_id is None:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la tabla primero.", parent=self)
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar este producto?", parent=self):
            self.db.eliminar(self.seleccion_id)
            self.limpiar()
            self.refrescar()

    def surtir(self):
        if self.seleccion_id is None:
            messagebox.showinfo("Selecciona un producto", "Elige un producto de la tabla primero.", parent=self)
            return
        nombre = self.var_nombre.get()
        n = PedirCantidadDialog(self, nombre).valor
        if n:
            actual = self.seleccion_id
            self.db.ajustar_cantidad(actual, n)
            self.refrescar()
            if self.tabla.exists(str(actual)):
                self.tabla.selection_set(str(actual))

    def al_seleccionar(self, _evento):
        sel = self.tabla.selection()
        if not sel:
            return
        self.seleccion_id = int(sel[0])
        codigo, nombre, precio, cantidad = self.tabla.item(sel[0], "values")
        self.var_codigo.set(codigo)
        self.var_nombre.set(nombre)
        self.var_precio.set(precio.replace("$", "").replace(",", ""))
        self.var_cantidad.set(str(cantidad))
        self.lbl_modo.config(text=f"✏ Editando: {nombre}", fg=NARANJA.base)

    def limpiar(self):
        self.seleccion_id = None
        for v in (self.var_codigo, self.var_nombre, self.var_precio, self.var_cantidad):
            v.set("")
        self.tabla.selection_remove(self.tabla.selection())
        self.lbl_modo.config(text="＋ Nuevo producto", fg=AZUL.base)


class PedirCantidadDialog(tk.Toplevel):

    def __init__(self, parent, producto):
        super().__init__(parent, bg=TARJETA)
        self.title("Surtir producto")
        self.valor = None
        self.resizable(False, False)
        centrar(self, 380, 300)

        encabezado(self, "📥", "Surtir", producto, NARANJA)
        cuerpo = tk.Frame(self, bg=TARJETA)
        cuerpo.pack(fill="both", expand=True, padx=26, pady=16)
        tk.Label(cuerpo, text="¿Cuántas piezas entraron?", bg=TARJETA, fg=SUAVE, font=f(10)).pack(anchor="w")
        self.var = tk.StringVar()
        self.ent = ttk.Entry(cuerpo, textvariable=self.var, font=f(20, "bold"), justify="center")
        self.ent.pack(fill="x", pady=(2, 4))
        self.lbl_error = tk.Label(cuerpo, text="", bg=TARJETA, fg=ROJO.base, font=f(10))
        self.lbl_error.pack(anchor="w")
        botones = tk.Frame(cuerpo, bg=TARJETA)
        botones.pack(fill="x", pady=(6, 0))
        Boton(botones, "Agregar al inventario", self.aceptar, NARANJA).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        Boton(botones, "Cancelar", self.destroy, NEUTRO, fg=TEXTO).pack(side="left")

        self.bind("<Return>", lambda _e: self.aceptar())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.ent.focus_set()
        hacer_modal(self, parent)

    def aceptar(self):
        try:
            n = int(self.var.get())
            if n <= 0:
                raise ValueError
        except ValueError:
            self.lbl_error.config(text="Escribe un número entero mayor a 0.")
            return
        self.valor = n
        self.destroy()


class VentasDiaWindow(tk.Toplevel):
    def __init__(self, parent, ventas):
        super().__init__(parent, bg=BG)
        self.title("Ventas del día")
        pantalla_completa(self)
        self.ventas = ventas

        encabezado(self, "📊", "Ventas del día", "Consulta lo vendido por fecha y el detalle de cada venta", NARANJA,
                   volver=self.destroy)
        cuerpo = tk.Frame(self, bg=BG)
        cuerpo.pack(fill="both", expand=True, padx=14, pady=14)

        barra = tarjeta(cuerpo)
        barra.pack(fill="x")
        fila = tk.Frame(barra, bg=TARJETA)
        fila.pack(fill="x", padx=12, pady=10)
        tk.Label(fila, text="📅 Fecha (AAAA-MM-DD):", bg=TARJETA, fg=TEXTO, font=f(11, "bold")).pack(side="left")
        self.var_fecha = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ent = ttk.Entry(fila, textvariable=self.var_fecha, width=12, font=f(12), justify="center")
        ent.pack(side="left", padx=8)
        ent.bind("<Return>", lambda _e: self.cargar())
        Boton(fila, "Ver", self.cargar, NARANJA, tam=11, pady=5).pack(side="left", padx=3)
        Boton(fila, "Hoy", self.hoy, AZUL, tam=11, pady=5).pack(side="left", padx=3)
        Boton(fila, "Siguiente ▶", lambda: self.mover(+1), NEUTRO, fg=TEXTO, tam=10, pady=5).pack(side="right")
        Boton(fila, "◀ Anterior", lambda: self.mover(-1), NEUTRO, fg=TEXTO, tam=10, pady=5).pack(
            side="right", padx=6)

        stats = tk.Frame(cuerpo, bg=BG)
        stats.pack(fill="x", pady=12)
        self.lbl_n = self._stat(stats, "VENTAS", AZUL, 0)
        self.lbl_total = self._stat(stats, "TOTAL DEL DÍA", VERDE, 1)
        self.lbl_prom = self._stat(stats, "TICKET PROMEDIO", MORADO, 2)
        for c in range(3):
            stats.columnconfigure(c, weight=1, uniform="stat")

        marco1 = tarjeta(cuerpo)
        marco1.pack(fill="both", expand=True)
        tk.Label(marco1, text="Ventas registradas", bg=TARJETA, fg=NARANJA.base, font=f(12, "bold")).pack(
            anchor="w", padx=12, pady=(8, 4))
        self.tabla = ttk.Treeview(marco1, columns=("id", "hora", "total", "pago", "cambio"), show="headings",
                                  selectmode="browse", height=7, style="Naranja.Treeview")
        for col, texto, ancho, ancla in [("id", "Venta #", 80, "center"), ("hora", "Hora", 110, "center"),
                                         ("total", "Total", 120, "e"), ("pago", "Pagó con", 120, "e"),
                                         ("cambio", "Cambio", 120, "e")]:
            self.tabla.heading(col, text=texto)
            self.tabla.column(col, width=ancho, anchor=ancla)
        preparar_tabla(self.tabla)
        self.tabla.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        self.tabla.bind("<<TreeviewSelect>>", self.mostrar_detalle)

        marco2 = tarjeta(cuerpo)
        marco2.pack(fill="both", expand=True, pady=(12, 0))
        self.lbl_detalle = tk.Label(marco2, text="Detalle de la venta (selecciona una arriba)", bg=TARJETA,
                                    fg=NARANJA.base, font=f(12, "bold"))
        self.lbl_detalle.pack(anchor="w", padx=12, pady=(8, 4))
        self.detalle = ttk.Treeview(marco2, columns=("nombre", "precio", "cant", "sub"), show="headings",
                                    height=5, style="Naranja.Treeview")
        for col, texto, ancho, ancla in [("nombre", "Producto", 300, "w"), ("precio", "Precio", 100, "e"),
                                         ("cant", "Cant.", 70, "center"), ("sub", "Subtotal", 110, "e")]:
            self.detalle.heading(col, text=texto)
            self.detalle.column(col, width=ancho, anchor=ancla)
        preparar_tabla(self.detalle)
        self.detalle.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        self.cargar()

    @staticmethod
    def _stat(padre, titulo, color, col):
        caja = tk.Frame(padre, bg=color.claro, highlightbackground=color.base, highlightthickness=1)
        caja.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0 if col == 2 else 6))
        tk.Label(caja, text=titulo, bg=color.claro, fg=color.base, font=f(9, "bold")).pack(pady=(10, 0))
        lbl = tk.Label(caja, text="0", bg=color.claro, fg=color.base, font=f(22, "bold"))
        lbl.pack(pady=(0, 10))
        return lbl

    def hoy(self):
        self.var_fecha.set(datetime.now().strftime("%Y-%m-%d"))
        self.cargar()

    def mover(self, dias):
        try:
            d = datetime.strptime(self.var_fecha.get().strip(), "%Y-%m-%d") + timedelta(days=dias)
        except ValueError:
            d = datetime.now()
        self.var_fecha.set(d.strftime("%Y-%m-%d"))
        self.cargar()

    def cargar(self):
        texto = self.var_fecha.get().strip()
        try:
            datetime.strptime(texto, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Fecha inválida", "Usa el formato AAAA-MM-DD, por ejemplo 2026-11-16.",
                                   parent=self)
            return
        self.tabla.delete(*self.tabla.get_children())
        self.detalle.delete(*self.detalle.get_children())
        self.lbl_detalle.config(text="Detalle de la venta (selecciona una arriba)")
        filas = self.ventas.ventas_del_dia(texto)
        for i, (id_, hora, total, pago, cambio) in enumerate(filas):
            self.tabla.insert("", "end", iid=str(id_), tags=(tag_fila(i),),
                              values=(id_, hora, dinero(total), dinero(pago), dinero(cambio)))
        suma = sum(r[2] for r in filas)
        self.lbl_n.config(text=str(len(filas)))
        self.lbl_total.config(text=dinero(suma))
        self.lbl_prom.config(text=dinero(suma / len(filas)) if filas else "$0.00")

    def mostrar_detalle(self, _e):
        self.detalle.delete(*self.detalle.get_children())
        sel = self.tabla.selection()
        if not sel:
            return
        self.lbl_detalle.config(text=f"Detalle de la venta #{sel[0]}")
        for i, (nombre, precio, cant, sub) in enumerate(self.ventas.detalle(int(sel[0]))):
            self.detalle.insert("", "end", tags=(tag_fila(i),),
                                values=(nombre, dinero(precio), cant, dinero(sub)))


class MenuPrincipal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.configure(bg=BG)
        self.title("Tienda de abarrotes")
        pantalla_completa(self)
        configurar_estilos(self)
        self.db = Database()
        self.ventas = VentasDB()
        self.auth = Auth()

        encabezado(self, "🏪", "Tienda de abarrotes", fecha_larga(), OSCURO,
                   volver=self.salir, texto_volver="✕  Salir")

        centro = tk.Frame(self, bg=BG)
        centro.pack(expand=True)
        centro.columnconfigure(0, minsize=780)
        TarjetaMenu(centro, "🛒", "VENTA", "Cobra productos a tus clientes", VERDE,
                    lambda: self._abrir("w_venta", VentaWindow, self.db, self.ventas)).grid(
            row=0, column=0, sticky="ew", pady=10)
        TarjetaMenu(centro, "📦", "AGREGAR PRODUCTOS", "Registra y surte tu inventario", AZUL,
                    self.abrir_productos).grid(row=1, column=0, sticky="ew", pady=10)

        fila = tk.Frame(centro, bg=BG)
        fila.grid(row=2, column=0, sticky="ew", pady=(10, 6))
        self.lbl_n = tk.Label(fila, text="", bg=AZUL.claro, fg=AZUL.base, font=f(10, "bold"), padx=12, pady=6)
        self.lbl_n.pack(side="left")
        self.lbl_bajo = tk.Label(fila, text="", bg=ROJO.claro, fg=ROJO.base, font=f(10, "bold"), padx=12, pady=6)
        self.lbl_bajo.pack(side="left", padx=8)

        Boton(centro, "🔒  Ventas del día (administrador)", self.abrir_ventas, NARANJA, tam=12, pady=12).grid(
            row=3, column=0, sticky="ew", pady=(6, 0))

        self.actualizar_resumen()
        self.bind("<FocusIn>", lambda e: self.actualizar_resumen() if e.widget is self else None)

    def salir(self):
        if messagebox.askyesno("Salir", "¿Cerrar el programa?", parent=self):
            self.destroy()

    def actualizar_resumen(self):
        n, bajo = self.db.resumen()
        self.lbl_n.config(text=f"📋 {n} productos registrados")
        if bajo:
            self.lbl_bajo.config(text=f"⚠ {bajo} con poco stock", bg=ROJO.claro, fg=ROJO.base)
        else:
            self.lbl_bajo.config(text="✔ Inventario al corriente", bg=VERDE.claro, fg=VERDE.base)

    def _abrir(self, atributo, clase, *args):
        ventana = getattr(self, atributo, None)
        if ventana is not None and ventana.winfo_exists():
            ventana.deiconify()
            ventana.lift()
            ventana.focus_force()
            return
        setattr(self, atributo, clase(self, *args))

    def pedir_login(self, mensaje):
        if not self.auth.existe():
            if not messagebox.askyesno(
                    "Administrador",
                    "Todavía no hay un usuario administrador.\n¿Quieres crearlo ahora?"):
                return False
            dlg = CredencialesDialog(
                self, "Crear administrador", confirmar=True,
                mensaje="Elige el usuario y la contraseña para proteger los productos y las ventas.")
            if not dlg.resultado:
                return False
            self.auth.crear(*dlg.resultado)
            messagebox.showinfo("Listo", "Administrador creado. Ahora inicia sesión.")

        dlg = CredencialesDialog(self, "Acceso de administrador", mensaje=mensaje)
        if not dlg.resultado:
            return False
        if not self.auth.validar(*dlg.resultado):
            messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos.")
            return False
        return True

    def abrir_productos(self):
        if self.pedir_login("Escribe tus datos para agregar o editar productos."):
            self._abrir("w_productos", ProductosWindow, self.db)

    def abrir_ventas(self):
        if self.pedir_login("Escribe tus datos para ver las ventas."):
            self._abrir("w_ventas", VentasDiaWindow, self.ventas)


if __name__ == "__main__":
    MenuPrincipal().mainloop()