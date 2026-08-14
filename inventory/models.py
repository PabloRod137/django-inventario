from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class Category(models.Model):
    name = models.CharField('nombre', max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField('nombre', max_length=150)
    contact_email = models.EmailField('email de contacto', blank=True)
    phone = models.CharField('teléfono', max_length=30, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'proveedor'
        verbose_name_plural = 'proveedores'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField('nombre', max_length=150)
    sku = models.CharField('SKU', max_length=50, unique=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='categoría',
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='proveedor',
    )
    unit_price = models.DecimalField('precio unitario', max_digits=10, decimal_places=2, default=0)
    current_stock = models.PositiveIntegerField('stock actual', default=0, editable=False)
    minimum_stock = models.PositiveIntegerField('stock mínimo', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'producto'
        verbose_name_plural = 'productos'

    def __str__(self):
        return f'{self.name} ({self.sku})'

    @property
    def is_below_minimum(self):
        return self.current_stock < self.minimum_stock


class StockMovement(models.Model):
    MOVEMENT_IN = 'in'
    MOVEMENT_OUT = 'out'
    MOVEMENT_CHOICES = [
        (MOVEMENT_IN, 'Entrada'),
        (MOVEMENT_OUT, 'Salida'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements', verbose_name='producto')
    movement_type = models.CharField('tipo', max_length=3, choices=MOVEMENT_CHOICES)
    quantity = models.PositiveIntegerField('cantidad')
    notes = models.CharField('notas', max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='stock_movements',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'movimiento de stock'
        verbose_name_plural = 'movimientos de stock'

    def __str__(self):
        return f'{self.get_movement_type_display()} de {self.quantity} — {self.product}'

    def clean(self):
        if self.movement_type == self.MOVEMENT_OUT and self.product_id and self.quantity:
            if self.quantity > self.product.current_stock:
                raise ValidationError('No hay stock suficiente para esta salida.')

    def save(self, *args, **kwargs):
        creating = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            if creating:
                product = Product.objects.select_for_update().get(pk=self.product_id)
                if self.movement_type == self.MOVEMENT_IN:
                    product.current_stock += self.quantity
                else:
                    product.current_stock -= self.quantity
                product.save(update_fields=['current_stock'])
