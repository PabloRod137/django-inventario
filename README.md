# Sistema de Inventario

Aplicación Django para controlar el stock y los movimientos (entradas/salidas) de productos.

Proyecto desarrollado como práctica del módulo de Django del máster de desarrollo full stack.

## Funcionalidades

- Registro, login y logout de usuarios
- Catálogo de productos con categoría, proveedor, precio y stock mínimo
- Registro de movimientos de entrada y salida, con validación de stock suficiente para salidas
- Stock actual calculado y actualizado automáticamente a partir de los movimientos
- Alertas de productos por debajo del stock mínimo
- Filtro de productos por categoría, proveedor y nombre
- Importación masiva de productos por CSV (crea o actualiza por SKU, y registra el stock inicial como movimiento de entrada)
- Gráfico de movimientos de los últimos 30 días (Chart.js)
- Panel de administración (Django admin) para gestionar categorías, proveedores, productos y movimientos

## Modelos

- `Category`: categoría de producto
- `Supplier`: proveedor
- `Product`: producto con stock actual (calculado) y stock mínimo
- `StockMovement`: movimiento de entrada o salida que actualiza el stock del producto de forma atómica

## Stack

- Python 3.12 + Django 6.1
- SQLite (desarrollo)
- Django templates + Bootstrap 5 + Chart.js

## Puesta en marcha

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visita `http://127.0.0.1:8000/`.

## Formato del CSV de importación

```csv
sku,name,category,supplier,unit_price,minimum_stock,initial_stock
P-001,Teclado mecánico,Periféricos,TechSupplies,45.90,10,25
```

## Estructura

```
config/       # configuración del proyecto Django
inventory/    # app principal: modelos, vistas, formularios, urls
templates/    # plantillas HTML
static/       # CSS/JS propios
```
