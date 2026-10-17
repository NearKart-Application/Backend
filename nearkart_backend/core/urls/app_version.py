from django.urls import path
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def app_version(request):
    """No auth required. Mobile calls this on launch to check if an update is mandatory."""
    return JsonResponse({
        'min_version': 1,    # build codes below this MUST update before using the app
        'latest_version': 1, # current store version — used to show optional update nudge
    })


urlpatterns = [path('version/', app_version)]
