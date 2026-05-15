from django.contrib import admin
from .models import Product, ProductVariant, ProductImage, Wishlist


class ProductVariantInline(admin.TabularInline):
    model  = ProductVariant
    extra  = 0
    fields = ['name', 'sku', 'price', 'stock_quantity']


class ProductImageInline(admin.TabularInline):
    model  = ProductImage
    extra  = 0
    fields = ['image_url', 'is_primary', 'order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ['name', 'store', 'category', 'status', 'is_visible', 'base_price', 'created_at']
    list_filter   = ['status', 'is_visible', 'category']
    search_fields = ['name', 'store__name']
    inlines       = [ProductVariantInline, ProductImageInline]
    readonly_fields = ['created_at', 'last_updated_at']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display  = ['user', 'product', 'created_at']
    search_fields = ['user__phone_number', 'product__name']
