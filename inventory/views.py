import csv
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
            qs = qs.filter(name__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['suppliers'] = Supplier.objects.all()
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_supplier'] = self.request.GET.get('supplier', '')
        context['query'] = self.request.GET.get('q', '')
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'inventory/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['movements'] = self.object.movements.select_related('created_by')[:50]
        context['movement_form'] = StockMovementForm()
        return context


@login_required
def product_create(request):
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
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.product = product
            movement.created_by = request.user
            try:
                movement.full_clean()
                movement.save()
                messages.success(request, 'Movimiento registrado correctamente.')
            except ValidationError as exc:
                messages.error(request, ' '.join(exc.messages))
        else:
            messages.error(request, 'Revisa los datos del movimiento.')
    return redirect('product_detail', pk=pk)


def low_stock_alert(request):
    products = [p for p in Product.objects.select_related('category', 'supplier') if p.is_below_minimum]
    return render(request, 'inventory/low_stock.html', {'products': products})


@login_required
def import_products(request):
    if request.method == 'POST':
        form = ProductImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            decoded = io.TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(decoded)
            created, updated, errors = 0, 0, []
            for row_number, row in enumerate(reader, start=2):
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
                    errors.append(f'Fila {row_number}: {exc}')

            messages.success(request, f'Importación completada: {created} creados, {updated} actualizados.')
            if errors:
                messages.warning(request, 'Errores: ' + '; '.join(errors))
            return redirect('product_list')
    else:
        form = ProductImportForm()
    return render(request, 'inventory/import_products.html', {'form': form})


def movements_chart(request):
    since = timezone.now() - timezone.timedelta(days=30)
    movements = StockMovement.objects.filter(created_at__gte=since)

    daily = defaultdict(lambda: {'in': 0, 'out': 0})
    for movement in movements:
        day = movement.created_at.date().isoformat()
        daily[day][movement.movement_type] += movement.quantity

    labels = sorted(daily.keys())
    context = {
        'labels_json': json.dumps(labels),
        'in_data_json': json.dumps([daily[day]['in'] for day in labels]),
        'out_data_json': json.dumps([daily[day]['out'] for day in labels]),
    }
    return render(request, 'inventory/movements_chart.html', context)
