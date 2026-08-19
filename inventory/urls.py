"""
URLs propias de la app "inventory", incluidas desde config/urls.py en la raíz del sitio.
"""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.ProductListView.as_view(), name='product_list'),
    path('nuevo/', views.product_create, name='product_create'),
    path('alertas/', views.low_stock_alert, name='low_stock_alert'),
    path('importar/', views.import_products, name='import_products'),
    path('graficos/', views.movements_chart, name='movements_chart'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('<int:pk>/movimiento/', views.movement_create, name='movement_create'),
    path('registro/', views.signup, name='signup'),
]
