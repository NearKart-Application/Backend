from django.urls import path
from .views import LocationOptionsView

urlpatterns = [
    path('', LocationOptionsView.as_view(), name='location-options'),
]
