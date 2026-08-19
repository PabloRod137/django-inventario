"""
Formularios de la app "inventory".

- SignUpForm: registro de usuarios.
- ProductForm: alta de productos (current_stock no aparece aquí a propósito:
  se gestiona solo desde StockMovement, ver models.py).
- StockMovementForm: registrar una entrada o salida de stock.
- ProductImportForm: subir un CSV para dar de alta/actualizar productos en lote.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Product, StockMovement


class SignUpForm(UserCreationForm):
    """Registro de usuario: añade el email (obligatorio) a lo que ya trae Django de serie."""

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ProductForm(forms.ModelForm):
    """
    Alta de un producto nuevo. Deliberadamente NO incluye 'current_stock':
    ese campo es de solo lectura a nivel de modelo (editable=False) y su
    único punto de entrada es registrar movimientos de stock, no editarlo
    directamente desde un formulario.
    """

    class Meta:
        model = Product
        fields = ['name', 'sku', 'category', 'supplier', 'unit_price', 'minimum_stock']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css_class


class StockMovementForm(forms.ModelForm):
    """
    Registrar un movimiento de entrada o salida de stock para un producto
    (el producto en sí se asigna en la vista, no aparece en este
    formulario porque ya se sabe de qué producto se trata por la URL).
    """

    class Meta:
        model = StockMovement
        fields = ['movement_type', 'quantity', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css_class


class ProductImportForm(forms.Form):
    """Subida del CSV para la importación masiva (ver inventory/views.py:import_products)."""

    csv_file = forms.FileField(label='Archivo CSV', widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))

    def clean_csv_file(self):
        # Comprobación mínima: que al menos tenga pinta de ser un CSV por
        # su extensión. No valida el contenido de verdad; eso ya lo hace
        # la vista fila a fila, recogiendo los errores que encuentre.
        csv_file = self.cleaned_data['csv_file']
        if not csv_file.name.lower().endswith('.csv'):
            raise forms.ValidationError('El archivo debe tener extensión .csv')
        return csv_file
