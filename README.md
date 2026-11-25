# Sistema de Gestión para Tienda de Abarrotes

Sistema de escritorio desarrollado en Python para administrar las operaciones principales de una tienda de abarrotes. Integra un módulo de punto de venta, control de inventario y consulta de ventas, mediante una interfaz gráfica intuitiva y una base de datos local.

El proyecto busca facilitar las actividades cotidianas de un pequeño establecimiento, permitiendo gestionar productos, registrar transacciones y mantener un control de las existencias.

## Características principales

### Punto de venta (POS)
- Búsqueda de productos por nombre o código de barras.
- Compatibilidad con lectores de códigos de barras que funcionan como entrada de teclado.
- Agregar productos a un carrito de compras.
- Modificar cantidades y eliminar productos del carrito.
- Cálculo automático del total de compra.
- Registro del importe recibido por el cliente.
- Cálculo automático del cambio que debe entregarse.
- Descuento automático de las existencias después de completar una venta.

### Gestión de inventario
- Registro de nuevos productos.
- Edición de información y precios.
- Eliminación de productos.
- Control de existencias.
- Registro de entradas de mercancía para resurtir productos.
- Búsqueda de productos por nombre o código.
- Identificación visual de productos con poco stock o agotados.
- Resumen del número de productos y valor del inventario.

### Historial y consulta de ventas
- Acceso protegido mediante credenciales de administrador.
- Consulta de ventas por fecha.
- Visualización del número de transacciones realizadas.
- Cálculo del total de ventas del día.
- Cálculo del ticket promedio.
- Consulta individual del detalle de cada venta.
- Visualización del importe pagado y el cambio entregado.

### Seguridad
- Configuración inicial de una cuenta de administrador.
- Acceso restringido a las funciones administrativas.
- Almacenamiento de contraseñas mediante hash PBKDF2-HMAC-SHA256 con salt aleatorio.
- Validación de credenciales mediante comparación segura.

### Interfaz gráfica
- Diseño visual moderno y organizado.
- Interfaz desarrollada con Tkinter y ttk.
- Ventanas adaptables a pantalla completa.
- Identificación visual mediante colores.
- Navegación sencilla entre los módulos del sistema.

## Tecnologías utilizadas

| Tecnología | Aplicación |
|---|---|
| Python 3 | Lenguaje principal |
| Tkinter | Interfaz gráfica |
| SQLite3 | Gestión de bases de datos |
| JSON | Almacenamiento de credenciales |
| hashlib | Generación de hashes de contraseñas |
| hmac | Comparación segura de credenciales |
| secrets | Generación de valores aleatorios criptográficos |

## Estructura del proyecto

El programa genera automáticamente los siguientes archivos en el directorio donde se encuentra el ejecutable o script:

```text
Tienda-Abarrotes/
│
├── abarrotes.py       # Programa principal
├── abarrotes.db       # Base de datos de productos e inventario
├── ventas.db          # Historial de ventas y detalles
└── admin.json         # Credenciales del administrador
```

Los archivos de bases de datos y credenciales se crean automáticamente al iniciar y configurar el sistema por primera vez.

## Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU-USUARIO/TU-REPOSITORIO.git
```

### 2. Acceder al directorio

```bash
cd TU-REPOSITORIO
```

### 3. Ejecutar el programa

Asegúrate de tener Python 3 instalado y ejecuta:

```bash
python abarrotes.py
```

**Nota:** Tkinter generalmente viene incluido con Python. En algunas distribuciones de Linux puede ser necesario instalar el paquete `python3-tk`.

## Primer inicio

Al ejecutar el programa por primera vez:

1. Se inicializan las bases de datos de productos y ventas.
2. El sistema solicita crear una cuenta de administrador.
3. Se configura un nombre de usuario y una contraseña.
4. Una vez completada la configuración, se muestra el menú principal.

Desde el menú principal se puede acceder al punto de venta, la gestión de productos y el historial de ventas.

## Almacenamiento de información

El sistema utiliza dos bases de datos SQLite independientes:

- **abarrotes.db:** almacena los productos, sus códigos, precios y cantidades disponibles.
- **ventas.db:** almacena las transacciones realizadas y el detalle de los productos vendidos.

Las credenciales administrativas se guardan por separado en `admin.json`, utilizando un mecanismo de derivación de hash con salt.

La información se conserva localmente, por lo que no es necesaria una conexión a Internet para utilizar el programa.

## Consideraciones

- Se recomienda realizar copias de seguridad periódicas de los archivos `.db` y `admin.json`.
- No se deben eliminar los archivos de almacenamiento si se desea conservar la información registrada.
- El sistema está diseñado para ejecutarse localmente en un equipo.
- La información no se sincroniza automáticamente entre diferentes dispositivos.

## Estado del proyecto

**Versión inicial en desarrollo.**

Este proyecto constituye una solución de gestión para pequeños establecimientos comerciales y una base para incorporar nuevas funcionalidades en futuras versiones.

## Autor

Merida Serralde Francisco Jared.

Desarrollado como proyecto de software utilizando Python, Tkinter y SQLite.

---

