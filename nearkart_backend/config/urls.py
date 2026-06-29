"""
NearKart — Root URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

API_V1 = 'api/v1/'

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns_media = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns_media = []

urlpatterns = [
    # ── ADMIN ─────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── API DOCS ──────────────────────────────────────────────
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # ── HEALTH CHECK ──────────────────────────────────────────
    path(API_V1 + 'health/', include('core.urls.health')),

    # ── APP VERSION (no auth) ─────────────────────────────────
    path(API_V1 + 'app/', include('core.urls.app_version')),

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
    path(API_V1 + 'billing/', include('apps.billing.urls')),

    # ── RESERVATIONS ──────────────────────────────────────────
    path(API_V1 + 'reservations/', include('apps.reservations.urls')),

    # ── ANALYTICS ─────────────────────────────────────────────
    path(API_V1 + 'analytics/', include('apps.analytics.urls')),

    # ── GROUPS ────────────────────────────────────────────────
    path(API_V1 + 'groups/', include('apps.groups.urls')),

    # ── ADMIN PANEL ───────────────────────────────────────────
    path(API_V1 + 'admin-panel/', include('apps.admin_panel.urls')),

    # ── NOTIFICATIONS ─────────────────────────────────────────
    path(API_V1 + 'notifications/', include('apps.notifications.urls')),

    # ── LOYALTY & REFERRALS ───────────────────────────────────────
    path(API_V1 + 'loyalty/', include('apps.loyalty.urls')),

    # ── INVENTORY ─────────────────────────────────────────────────────
    path(API_V1 + 'inventory/', include('apps.inventory.urls')),
] + urlpatterns_media

