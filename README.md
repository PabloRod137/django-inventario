# 📦 Sistema de Inventario

Aplicación Django para controlar el stock de un catálogo de productos: qué entra, qué sale, cuánto queda de cada cosa y cuándo hay que reponer. Es uno de los proyectos que he desarrollado como práctica del módulo de Django dentro de mi máster de desarrollo full stack.

> **¿Qué resuelve exactamente?** El típico Excel de "entradas y salidas" que se acaba desincronizando de la realidad, pero llevado a una app donde el stock se recalcula solo a partir de su propio historial de movimientos, así que nunca puede quedar "mal cuadrado".

## 🧭 Índice

- [¿Qué puedes hacer con esta app?](#-qué-puedes-hacer-con-esta-app)
- [Cómo está pensado por dentro](#-cómo-está-pensado-por-dentro)
- [Stack técnico](#-stack-técnico)
- [Ponerlo en marcha en tu máquina](#-ponerlo-en-marcha-en-tu-máquina)
- [Cómo probarlo rápido](#-cómo-probarlo-rápido)
- [Formato del CSV de importación](#-formato-del-csv-de-importación)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Decisiones de diseño (y sus límites)](#-decisiones-de-diseño-y-sus-límites)
- [Posibles mejoras futuras](#-posibles-mejoras-futuras)

## ✅ ¿Qué puedes hacer con esta app?

- **Registrarte, iniciar sesión y cerrarla.**
- **Consultar el catálogo de productos**, con filtros por categoría, proveedor y nombre — sin necesidad de tener cuenta.
- **Dar de alta un producto** nuevo (empieza siempre con stock 0; se sube registrando movimientos).
- **Registrar entradas y salidas de stock** desde la ficha de cada producto, con notas opcionales. **No se puede registrar una salida mayor que el stock disponible**: el sistema lo rechaza con un mensaje claro.
- **Ver el historial completo de movimientos** de cada producto (quién, cuándo, cuánto, de qué tipo).
- **Consultar las "Alertas de stock"**: un listado con todos los productos que están por debajo de su stock mínimo.
- **Importar productos en bloque desde un CSV** (crea los que no existan y actualiza los que ya tengan ese SKU; si se indica un stock inicial, queda registrado como un movimiento de entrada más, no como un truco aparte).
- **Ver un gráfico** con las entradas y salidas de los últimos 30 días.
- **Gestionarlo todo desde el panel de administración de Django** (`/admin/`).

## 🧠 Cómo está pensado por dentro

Cuatro modelos en la app `inventory`:

```
Category (1) ---- (N) Product
Supplier (1) ---- (N) Product
Product  (1) ---- (N) StockMovement    -> el historial de entradas/salidas de cada producto
```

La decisión más importante del proyecto es esta: **`Product.current_stock` no se edita nunca a mano**. No hay ningún formulario ni pantalla del admin donde se pueda escribir directamente "este producto tiene 50 unidades". El único sitio donde ese número cambia es dentro de `StockMovement.save()`, que suma o resta la cantidad correspondiente cada vez que se registra un movimiento. La ventaja es que el stock mostrado siempre coincide, por construcción, con la suma de su propio historial — es imposible que se desincronicen porque solo hay un camino para cambiarlo.

Esto, sin embargo, abre la puerta al problema clásico de la **condición de carrera**: si dos personas registran a la vez una salida del mismo producto y solo queda stock para una de las dos operaciones, ambas podrían comprobar "hay stock suficiente" antes de que ninguna termine de guardar, y el stock acabaría en negativo. `StockMovement.save()` lo evita bloqueando la fila del producto (`select_for_update()`) dentro de una transacción **antes** de comprobar la cantidad disponible, así que la segunda petición que llega tiene que esperar a que la primera termine y ve el stock ya actualizado. Es el mismo patrón que se usaría en un sistema de facturación o de venta de entradas; aquí se aplica al control de inventario, con comentarios explicando el porqué paso a paso en `inventory/models.py`.

## 🛠️ Stack técnico

| Pieza | Tecnología |
|---|---|
| Backend | Python 3.12 + Django 6.1 |
| Base de datos | SQLite (desarrollo/demo; en producción, PostgreSQL o MySQL) |
| Frontend | Plantillas de Django + Bootstrap 5 (CDN) |
| Gráficos | Chart.js (CDN, sin build ni npm) |
| Autenticación | `django.contrib.auth` |

## 🚀 Ponerlo en marcha en tu máquina

```bash
# 1. Clona el repo y entra en la carpeta
git clone https://github.com/PabloRod137/django-inventario.git
cd django-inventario

# 2. Crea y activa un entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. Aplica las migraciones (crea la base de datos)
python manage.py migrate

# 5. Crea un usuario administrador
python manage.py createsuperuser

# 6. Arranca el servidor
python manage.py runserver
```

Abre **http://127.0.0.1:8000/** en el navegador.

### ✅ Tests automatizados

La lógica de StockMovement (entradas/salidas, validación de stock suficiente, alerta de mínimo) tiene tests:

```bash
python manage.py test
```

## 🔍 Cómo probarlo rápido

1. Regístrate en `/registro/`.
2. Crea un producto desde "Nuevo producto" (empezará con stock 0).
3. Ve a su ficha y registra un movimiento de "Entrada" (por ejemplo, 20 unidades). El stock se actualizará al momento.
4. Intenta registrar una "Salida" mayor de la que hay: debería rechazarse con un aviso claro.
5. Prueba a importar el CSV de ejemplo de más abajo desde "Importar CSV".
6. Échale un ojo a "Alertas de stock" y a "Gráficos" para ver el resto de funcionalidades.

## 📄 Formato del CSV de importación

```csv
sku,name,category,supplier,unit_price,minimum_stock,initial_stock
P-001,Teclado mecánico,Perifericos,TechSupplies,45.90,10,25
P-002,Monitor 24 pulgadas,Monitores,DisplayCo,149.00,5,8
```

- Si el `sku` ya existe, ese producto se **actualiza** con el resto de columnas.
- Si no existe, se **crea**, y si además trae `initial_stock`, se registra automáticamente como un movimiento de entrada (queda reflejado en su historial, no es un atajo que se salte el sistema de movimientos).
- `category` y `supplier` se crean solos si no existían todavía; no hace falta darlos de alta a mano antes de importar.

## 📁 Estructura del proyecto

```
config/               # configuración del proyecto Django (settings, urls raíz)
inventory/              # la app: modelos, vistas, formularios, admin, urls
    models.py             # Category, Supplier, Product, StockMovement (aquí vive la lógica de stock)
    views.py               # catálogo, ficha de producto, alertas, importación CSV, gráficos
    forms.py                 # formularios de registro, producto, movimiento e importación
    admin.py                   # configuración del panel de administración
templates/             # plantillas HTML (base.html + una por vista)
static/                # CSS propio
```

## 🎯 Decisiones de diseño (y sus límites)

- **El stock nunca se edita directamente**, solo a través de movimientos. Es la decisión que sostiene todo lo demás: garantiza que el número que se ve siempre es coherente con el historial.
- **La protección contra condiciones de carrera usa `select_for_update()`**, el patrón estándar en Django/SQL para esto. En SQLite (la base de datos de este proyecto en desarrollo) el bloqueo no se aplica de verdad, pero el código es el correcto para producción con PostgreSQL o MySQL.
- **Las alertas de stock mínimo se calculan trayendo todos los productos y filtrando en Python** (porque comparar dos columnas del mismo modelo, `current_stock < minimum_stock`, no se puede expresar con un simple `.filter()` sin usar `F()` expressions). Para un catálogo pequeño/mediano esto es perfectamente razonable; con miles de productos convendría moverlo a una consulta con `F()`.
- **Los movimientos de stock no se editan ni se borran** una vez creados: si algo se registró mal, lo correcto es un movimiento de signo contrario para corregirlo, igual que en contabilidad. Mantiene el historial fiable de principio a fin.

## 🔮 Posibles mejoras futuras

- Aviso por email automático cuando un producto cae por debajo de su stock mínimo (la infraestructura de correo ya está configurada con el backend de consola).
- Mover el cálculo de "productos bajo mínimo" a una consulta con `F()` para que escale mejor con catálogos grandes.
- Exportar el historial de movimientos a CSV/Excel, igual que ya se puede importar.
- Permitir editar o dar de baja un producto (de momento solo se puede crear).
