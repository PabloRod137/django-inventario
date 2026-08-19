"""
Vistas de la app "inventory".

La vista más "delicada" es movement_create, porque ahí es donde se decide
si una salida de stock es válida o no. La validación de verdad (la que
protege contra condiciones de carrera) está en StockMovement.save()
(ver models.py); aquí solo llamamos a full_clean()/save() y traducimos
el resultado a un mensaje para el usuario.
"""

import csv
import datetime
import io
import json
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import DetailView, ListView

from .forms import ProductForm, ProductImportForm, SignUpForm, StockMovementForm
from .models import Category, Product, StockMovement, Supplier


def signup(request):
    """Registro de un usuario nuevo. Si todo va bien, lo deja logueado directamente."""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Cuenta creada correctamente. ¡Bienvenido!')
            return redirect('product_list')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


class ProductListView(ListView):
    """Catálogo de productos, con filtros opcionales por categoría, proveedor y nombre (todos por querystring)."""

    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        qs = Product.objects.select_related('category', 'supplier')
        category_id = self.request.GET.get('category')
        supplier_id = self.request.GET.get('supplier')
        query = self.request.GET.get('q')
        if category_id:
            qs = qs.filter(category_id=category_id)
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if query:
            qs = qs.filter(name__icontains=query)  # búsqueda "contiene", sin distinguir mayúsculas/minúsculas
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Las listas completas de categorías/proveedores se usan para
        # rellenar los desplegables de filtro en la plantilla.
        context['categories'] = Category.objects.all()
        context['suppliers'] = Supplier.objects.all()
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_supplier'] = self.request.GET.get('supplier', '')
        context['query'] = self.request.GET.get('q', '')
        return context


class ProductDetailView(DetailView):
    """Ficha de un producto: sus datos, el formulario para registrar un movimiento y su historial reciente."""

    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Limitamos a los 50 movimientos más recientes: para un historial
        # que pueda crecer mucho, no tiene sentido cargarlo entero en cada
        # visita a la ficha del producto.
        context['movements'] = self.object.movements.select_related('created_by')[:50]
        context['movement_form'] = StockMovementForm()
        return context


@login_required
def product_create(request):
    """Da de alta un producto nuevo. Su stock empieza siempre en 0 (se sube registrando un movimiento de entrada)."""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, 'Producto creado correctamente.')
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {'form': form})


@login_required
def movement_create(request, pk):
    """
    Registra un movimiento de entrada o salida sobre un producto concreto.

    El trabajo "de verdad" (bloquear el producto, comprobar que hay stock
    suficiente para una salida, actualizar current_stock) sucede dentro de
    StockMovement.save() de forma atómica; aquí nos limitamos a validar el
    formulario y a mostrar el resultado.
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.product = product
            movement.created_by = request.user
            try:
                # full_clean() dispara StockMovement.clean(), la validación
                # "amable" de stock suficiente. save() añade además, por
                # dentro, la comprobación robusta contra condiciones de
                # carrera (ver el docstring de StockMovement.save()).
                movement.full_clean()
                movement.save()
                messages.success(request, 'Movimiento registrado correctamente.')
            except ValidationError as exc:
                messages.error(request, ' '.join(exc.messages))
        else:
            messages.error(request, 'Revisa los datos del movimiento.')
    return redirect('product_detail', pk=pk)


def low_stock_alert(request):
    """
    Productos por debajo de su stock mínimo.

    is_below_minimum es una @property de Python (se calcula al vuelo, no
    es una columna de la base de datos), así que no se puede usar
    directamente en un .filter() de Django. Por eso aquí se trae la lista
    completa de productos y se filtra "a mano" con una list comprehension.
    Para un catálogo con muchísimos productos convendría mover esta lógica
    a una consulta con F() (comparando current_stock con minimum_stock
    directamente en SQL), pero para el tamaño de este proyecto no compensa
    la complejidad añadida.
    """
    products = [p for p in Product.objects.select_related('category', 'supplier') if p.is_below_minimum]
    return render(request, 'inventory/low_stock.html', {'products': products})


@login_required
def import_products(request):
    """
    Importación masiva de productos desde un CSV.

    Formato esperado (cabecera incluida):
        sku,name,category,supplier,unit_price,minimum_stock,initial_stock

    Si el SKU ya existe, el producto se ACTUALIZA con los nuevos datos; si
    no existe, se CREA. Categoría y proveedor se crean automáticamente si
    no existían todavía (get_or_create), para no obligar a darlos de alta
    a mano antes de importar. Si se indica un 'initial_stock' al crear un
    producto nuevo, se registra como un movimiento de entrada normal (no
    se toca current_stock directamente), así ese stock inicial queda
    reflejado también en el historial de movimientos.

    Fila a fila: si una fila da error (falta una columna, un número no es
    válido...) se anota el motivo y se sigue con las siguientes filas, en
    vez de abortar toda la importación por un solo error.
    """
    if request.method == 'POST':
        form = ProductImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            # csv.DictReader necesita un iterable de texto, no de bytes;
            # TextIOWrapper "envuelve" el archivo subido para decodificarlo.
            decoded = io.TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(decoded)
            created, updated, errors = 0, 0, []
            for row_number, row in enumerate(reader, start=2):  # empezamos en 2: la fila 1 es la cabecera
                try:
                    sku = row['sku'].strip()
                    name = row['name'].strip()
                    unit_price = row.get('unit_price') or 0
                    minimum_stock = row.get('minimum_stock') or 0
                    initial_stock = int(row.get('initial_stock') or 0)

                    category = None
                    if row.get('category'):
                        category, _ = Category.objects.get_or_create(name=row['category'].strip())
                    supplier = None
                    if row.get('supplier'):
                        supplier, _ = Supplier.objects.get_or_create(name=row['supplier'].strip())

                    product, was_created = Product.objects.update_or_create(
                        sku=sku,
                        defaults={
                            'name': name,
                            'category': category,
                            'supplier': supplier,
                            'unit_price': unit_price,
                            'minimum_stock': minimum_stock,
                        },
                    )
                    if was_created and initial_stock:
                        StockMovement.objects.create(
                            product=product,
                            movement_type=StockMovement.MOVEMENT_IN,
                            quantity=initial_stock,
                            notes='Stock inicial (importación CSV)',
                            created_by=request.user,
                        )
                    created += 1 if was_created else 0
                    updated += 0 if was_created else 1
                except (KeyError, ValueError) as exc:
                    # KeyError: falta una columna obligatoria en esa fila.
                    # ValueError: initial_stock no se pudo convertir a número.
                    errors.append(f'Fila {row_number}: {exc}')

            messages.success(request, f'Importación completada: {created} creados, {updated} actualizados.')
            if errors:
                messages.warning(request, 'Errores: ' + '; '.join(errors))
            return redirect('product_list')
    else:
        form = ProductImportForm()
    return render(request, 'inventory/import_products.html', {'form': form})


def movements_chart(request):
    """
    Prepara los datos para el gráfico de entradas/salidas de los últimos
    30 días. Aquí solo se agregan los números (cuánto entró y cuánto salió
    cada día); quien dibuja el gráfico de verdad es Chart.js en el
    navegador, a partir de este JSON (ver templates/inventory/movements_chart.html).
    """
    since = timezone.now() - datetime.timedelta(days=30)
    movements = StockMovement.objects.filter(created_at__gte=since)

    # defaultdict con una fábrica de diccionarios {'in': 0, 'out': 0}: así
    # no hace falta comprobar "¿ya existe esta fecha en el diccionario?"
    # antes de sumarle una cantidad, se crea sola la primera vez que se usa.
    daily = defaultdict(lambda: {'in': 0, 'out': 0})
    for movement in movements:
        # Igual que en los otros dos proyectos: para no arrastrar el mismo
        # tipo de desfase de zona horaria, convertimos a hora local antes
        # de decidir "a qué día pertenece" cada movimiento.
        day = timezone.localtime(movement.created_at).date().isoformat()
        daily[day][movement.movement_type] += movement.quantity

    labels = sorted(daily.keys())
    context = {
        # Chart.js necesita JSON de verdad en el HTML, no listas de Python;
        # json.dumps() hace esa conversión antes de pasarlo a la plantilla
        # (donde se inserta con el filtro |safe, ver movements_chart.html).
        'labels_json': json.dumps(labels),
        'in_data_json': json.dumps([daily[day]['in'] for day in labels]),
        'out_data_json': json.dumps([daily[day]['out'] for day in labels]),
    }
    return render(request, 'inventory/movements_chart.html', context)
