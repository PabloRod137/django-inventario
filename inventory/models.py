"""
Modelos de la app "inventory".

Cuatro modelos, relacionados así:

    Category (1) ---- (N) Product
    Supplier (1) ---- (N) Product
    Product  (1) ---- (N) StockMovement   -> el historial de entradas/salidas de cada producto

La pieza central es StockMovement.save(): ahí es donde se actualiza el
stock de un producto de forma segura cada vez que se registra un
movimiento. Vale la pena leer sus comentarios con calma.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class Category(models.Model):
    """Categoría de producto (Periféricos, Monitores...). Simple a propósito."""

    name = models.CharField('nombre', max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Proveedor al que se le compran los productos."""

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
    """
    Un producto del catálogo.

    IMPORTANTE: `current_stock` no se edita nunca a mano (ni desde un
    formulario, ni desde el admin: fíjate en editable=False y en que
    ProductAdmin lo marca como readonly_fields). Su único punto de entrada
    es StockMovement.save(), que lo va sumando o restando según se
    registran movimientos de entrada o salida. Esto garantiza que el
    stock mostrado siempre cuadra con la suma de su historial de
    movimientos: no hay dos sitios distintos donde "el stock" pueda
    quedar desincronizado.
    """

    name = models.CharField('nombre', max_length=150)
    sku = models.CharField('SKU', max_length=50, unique=True)  # código único de referencia del producto
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
        """True si hay que reponer: el stock actual no llega al mínimo marcado."""
        return self.current_stock < self.minimum_stock


class StockMovement(models.Model):
    """
    Un movimiento de stock: una entrada (compra, reposición...) o una
    salida (venta, uso interno...) de una cantidad concreta de un producto.

    Los movimientos son el "libro de cuentas" del inventario: no se editan
    ni se borran una vez creados (no hay vista ni opción de admin para
    ello), solo se añaden nuevos. Si algo se registró mal, lo correcto es
    crear un movimiento de signo contrario para corregirlo, igual que en
    contabilidad.
    """

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
        """
        Validación "amable": se usa cuando se rellena el formulario, para
        poder avisar al usuario con un mensaje claro ANTES de intentar
        guardar. No es la única barrera contra quedarse con stock negativo:
        ver el comentario en save() sobre por qué hace falta una segunda
        comprobación ahí.
        """
        if (
            self.movement_type == self.MOVEMENT_OUT
            and self.product_id and self.quantity
            and self.quantity > self.product.current_stock
        ):
            raise ValidationError('No hay stock suficiente para esta salida.')

    def save(self, *args, **kwargs):
        """
        Guarda el movimiento y actualiza el stock del producto en la misma
        operación atómica, para que nunca queden "a medias" (movimiento
        guardado pero stock sin actualizar, o viceversa).

        Por qué se vuelve a comprobar el stock aquí, y no basta con
        clean(): imagina que hay 3 unidades en stock y dos personas
        registran, casi a la vez, una salida de 3 unidades cada una. Las
        dos podrían pasar la validación de clean() (ambas ven "3 en stock,
        pido 3, vale") antes de que ninguna haya terminado de guardar. Si
        luego las dos actualizaran el stock sin más, acabaríamos con
        current_stock en -3, algo que PositiveIntegerField ni siquiera
        debería permitir.

        La solución es select_for_update(): dentro de una transacción,
        bloquea la fila del producto hasta que la transacción termina. Si
        dos peticiones llegan a la vez, la segunda tiene que ESPERAR a que
        la primera acabe (momento en el que el stock ya estará
        actualizado), así que su comprobación se hace con el dato correcto
        y ya no puede colarse. Por eso el bloqueo se pide primero, y solo
        si la cantidad es válida se guarda el movimiento y se actualiza el
        stock.

        Nota para quien esté aprendiendo: en SQLite (la base de datos de
        este proyecto en desarrollo) select_for_update() no bloquea de
        verdad la fila, así que este escenario no se puede reproducir en
        local; pero el código es el correcto para producción con
        PostgreSQL o MySQL, que sí lo respetan.
        """
        creating = self._state.adding
        with transaction.atomic():
            if creating:
                product = Product.objects.select_for_update().get(pk=self.product_id)
                if self.movement_type == self.MOVEMENT_OUT and self.quantity > product.current_stock:
                    raise ValidationError('No hay stock suficiente para esta salida.')

                super().save(*args, **kwargs)

                if self.movement_type == self.MOVEMENT_IN:
                    product.current_stock += self.quantity
                else:
                    product.current_stock -= self.quantity
                product.save(update_fields=['current_stock'])
            else:
                # Los movimientos no se editan desde la app (ver docstring
                # de la clase), pero si algún día se guardase un cambio que
                # no sea de creación (por ejemplo, corregir unas notas desde
                # el admin), no queremos volver a aplicar el ajuste de stock.
                super().save(*args, **kwargs)
