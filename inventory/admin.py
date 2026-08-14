from django.contrib import admin

from .models import Category, Product, StockMovement, Supplier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_email', 'phone')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'supplier', 'current_stock', 'minimum_stock', 'is_below_minimum')
    list_filter = ('category', 'supplier')
    search_fields = ('name', 'sku')
    readonly_fields = ('current_stock',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'created_by', 'created_at')
    list_filter = ('movement_type', 'product__category')
    search_fields = ('product__name', 'product__sku')
    date_hierarchy = 'created_at'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.full_clean()
        obj.save()
