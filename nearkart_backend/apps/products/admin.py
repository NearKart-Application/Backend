"""
NearKart — Products Admin
Shopify-grade admin for Product, ProductVariant, ProductImage,
Wishlist, ProductReview.
"""
from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from .models import (
    Product, ProductVariant, ProductImage,
    Wishlist, ProductReview,
)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _badge(text, bg, color):
    return format_html(
        '<span style="padding:2px 8px;border-radius:12px;font-size:11px;'
        'font-weight:600;background:{};color:{}">{}</span>',
        bg, color, text
    )


# ─── Inlines ──────────────────────────────────────────────────────────────────

class ProductVariantInline(admin.TabularInline):
    model   = ProductVariant
    extra   = 0
    fields  = ['name', 'sku', 'price', 'mrp', 'cost_price',
               'stock_quantity', 'low_stock_threshold', 'accepts_custom_orders']
    show_change_link = True


class ProductImageInline(admin.TabularInline):
    model   = ProductImage
    extra   = 0
    fields  = ['image_url', 'is_primary', 'order']
    ordering = ['order']


# ─── Bulk actions ─────────────────────────────────────────────────────────────

@admin.action(description='Make selected products visible')
def make_visible(modeladmin, request, queryset):
    updated = queryset.update(is_visible=True)
    modeladmin.message_user(request, f'{updated} product(s) made visible.')


@admin.action(description='Hide selected products')
def make_invisible(modeladmin, request, queryset):
    updated = queryset.update(is_visible=False)
    modeladmin.message_user(request, f'{updated} product(s) hidden.')


@admin.action(description='Approve selected products (set Active)')
def approve_products(modeladmin, request, queryset):
    from .models import ProductStatus
    updated = queryset.update(status=ProductStatus.ACTIVE)
    modeladmin.message_user(request, f'{updated} product(s) approved and set to Active.')


@admin.action(description='Blacklist selected products')
def blacklist_products(modeladmin, request, queryset):
    from .models import ProductStatus
    updated = queryset.update(status=ProductStatus.BLACKLISTED, is_visible=False)
    modeladmin.message_user(request, f'{updated} product(s) blacklisted and hidden.')


# ─── Product Admin ────────────────────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display   = [
        'name', 'store', 'category', 'status_badge',
        'total_stock', 'base_price', 'visible_badge', 'created_at',
    ]
    list_filter    = ['status', 'is_visible', 'category']
    search_fields  = ['name', 'store__name', 'store__owner__phone_number', 'product_code']
    ordering       = ['-created_at']
    date_hierarchy = 'created_at'
    list_per_page  = 25
    show_full_result_count = False
    list_select_related    = ['store']
    raw_id_fields  = ['store']
    readonly_fields = ['product_code', 'previous_price', 'created_at', 'last_updated_at']
    actions        = [make_visible, make_invisible, approve_products, blacklist_products]
    inlines        = [ProductVariantInline, ProductImageInline]

    fieldsets = (
        ('Product Info', {'fields': ('store', 'product_code', 'name', 'description',
                                     'category', 'subcategory', 'festival_tag')}),
        ('Pricing',      {'fields': ('base_price', 'previous_price')}),
        ('Status',       {'fields': ('status', 'is_visible')}),
        ('Timestamps',   {'fields': ('created_at', 'last_updated_at'), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _total_stock=Sum('variants__stock_quantity')
        )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'active':       ('#d4edda', '#155724'),
            'draft':        ('#fff3cd', '#856404'),
            'inactive':     ('#e2e3e5', '#383d41'),
            'out_of_stock': ('#f8d7da', '#721c24'),
            'blacklisted':  ('#721c24', '#ffffff'),
        }
        bg, color = colors.get(obj.status, ('#e2e3e5', '#333'))
        return _badge(obj.get_status_display(), bg, color)

    @admin.display(description='Total Stock', ordering='_total_stock')
    def total_stock(self, obj):
        qty = obj._total_stock or 0
        if qty == 0:
            return format_html('<span style="color:#721c24;font-weight:600">0</span>')
        elif qty <= 5:
            return format_html('<span style="color:#856404;font-weight:600">{}</span>', qty)
        return format_html('<span style="color:#155724;font-weight:600">{}</span>', qty)

    @admin.display(description='Visible', ordering='is_visible')
    def visible_badge(self, obj):
        if obj.is_visible:
            return _badge('Yes', '#d4edda', '#155724')
        return _badge('Hidden', '#e2e3e5', '#383d41')


# ─── Wishlist Admin ───────────────────────────────────────────────────────────

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display    = ['user', 'product', 'created_at']
    search_fields   = ['user__phone_number', 'product__name']
    date_hierarchy  = 'created_at'
    list_per_page   = 50
    show_full_result_count = False
    list_select_related    = ['user', 'product']
    raw_id_fields   = ['user', 'product']
    readonly_fields = ['created_at', 'updated_at']


# ─── Product Review Admin ─────────────────────────────────────────────────────

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display    = ['product', 'reviewer_phone', 'rating_stars', 'created_at']
    list_filter     = ['rating']
    search_fields   = ['product__name', 'reviewer__phone_number', 'content']
    date_hierarchy  = 'created_at'
    list_per_page   = 25
    list_select_related    = ['product', 'reviewer']
    raw_id_fields   = ['product', 'reviewer', 'invoice']
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='Reviewer', ordering='reviewer__phone_number')
    def reviewer_phone(self, obj):
        return obj.reviewer.phone_number

    @admin.display(description='Rating', ordering='rating')
    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        colors = {5: '#155724', 4: '#155724', 3: '#856404', 2: '#721c24', 1: '#721c24'}
        return format_html(
            '<span style="color:{};font-size:13px">{}</span>',
            colors.get(obj.rating, '#333'), stars
        )
