"""
NearKart — Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

API_V1 = 'api/v1/'

urlpatterns = [
    # ── ADMIN ─────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── API DOCS ──────────────────────────────────────────────
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # ── HEALTH CHECK ──────────────────────────────────────────
    path(API_V1 + 'health/', include('core.urls.health')),

    # ── AUTH ──────────────────────────────────────────────────
    path(API_V1 + 'auth/', include('apps.auth_app.urls')),

    # ── STORES ────────────────────────────────────────────────
    path(API_V1 + 'stores/', include('apps.stores.urls')),

    # ── PRODUCTS ──────────────────────────────────────────────
    path(API_V1 + 'products/', include('apps.products.urls')),

    # ── VIDEOS ────────────────────────────────────────────────
    path(API_V1 + 'videos/', include('apps.videos.urls')),

    # ── CHAT ──────────────────────────────────────────────────
    path(API_V1 + 'conversations/', include('apps.chat.urls')),

    # ── BILLING ───────────────────────────────────────────────
    path(API_V1 + 'invoices/', include('apps.billing.urls.invoices')),
    path(API_V1 + 'wallet/', include('apps.billing.urls.wallet')),
    path(API_V1 + 'expenses/', include('apps.billing.urls.expenses')),
    path(API_V1 + 'referral/', include('apps.billing.urls.referral')),

    # ── RESERVATIONS ──────────────────────────────────────────
    path(API_V1 + 'reservations/', include('apps.reservations.urls')),

    # ── ANALYTICS ─────────────────────────────────────────────
    path(API_V1 + 'analytics/', include('apps.analytics.urls')),

    # ── GROUPS ────────────────────────────────────────────────
    path(API_V1 + 'groups/', include('apps.groups.urls')),

    # ── ADMIN PANEL ───────────────────────────────────────────
    path(API_V1 + 'admin-panel/', include('apps.admin_panel.urls')),
]

# ── DEBUG TOOLBAR ─────────────────────────────────────────────
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
