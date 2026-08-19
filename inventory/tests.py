"""
Tests automatizados de la app "inventory".

Se centran en StockMovement, que es donde vive toda la lógica delicada del
proyecto: que las entradas sumen y las salidas resten al stock, que no se
pueda registrar una salida mayor que el stock disponible, y que la alerta
de "stock bajo mínimo" se calcule bien. Para ejecutarlos:

    python manage.py test
"""

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Product, StockMovement


class StockMovementTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Producto de prueba', sku='TEST-001', minimum_stock=5)

    def test_una_entrada_suma_al_stock(self):
        StockMovement.objects.create(product=self.product, movement_type=StockMovement.MOVEMENT_IN, quantity=10)
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 10)

    def test_una_salida_resta_al_stock(self):
        StockMovement.objects.create(product=self.product, movement_type=StockMovement.MOVEMENT_IN, quantity=10)
        StockMovement.objects.create(product=self.product, movement_type=StockMovement.MOVEMENT_OUT, quantity=4)

        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 6)

    def test_no_permite_una_salida_mayor_que_el_stock_disponible(self):
        # El producto empieza con stock 0, así que cualquier salida debería fallar.
        movimiento = StockMovement(product=self.product, movement_type=StockMovement.MOVEMENT_OUT, quantity=1)
        with self.assertRaises(ValidationError):
            movimiento.full_clean()

        # Y el stock no debe haberse tocado.
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 0)

    def test_stock_por_debajo_del_minimo_se_detecta(self):
        StockMovement.objects.create(product=self.product, movement_type=StockMovement.MOVEMENT_IN, quantity=3)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_below_minimum)  # 3 < mínimo (5)

    def test_stock_por_encima_del_minimo_no_genera_alerta(self):
        StockMovement.objects.create(product=self.product, movement_type=StockMovement.MOVEMENT_IN, quantity=10)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_below_minimum)  # 10 >= mínimo (5)
