from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LocationMaster


class LocationOptionsView(APIView):
    """
    Public endpoint — no auth required (used by mobile app during registration).
    """
    authentication_classes = []
    permission_classes      = []

    @extend_schema(
        summary="Get location options (State / District / City)",
        description=(
            "Returns location options for one level of the hierarchy.\n\n"
            "**How to use:**\n"
            "- `field=state` → returns all 36 Indian states/UTs\n"
            "- `field=district&state=Telangana` → returns districts inside Telangana\n"
            "- `field=city&state=Telangana&district=Hyderabad` → returns cities inside Hyderabad district\n\n"
            "**`field`** controls *what you want back*, not the state/district name."
        ),
        parameters=[
            OpenApiParameter(
                "field",
                str,
                required=True,
                enum=["state", "district", "city"],
                description="Level to fetch: `state` | `district` | `city`",
            ),
            OpenApiParameter(
                "state",
                str,
                required=False,
                description="State name — required when field=district or field=city",
                examples=[
                    OpenApiExample("Telangana",      value="Telangana"),
                    OpenApiExample("Andhra Pradesh", value="Andhra Pradesh"),
                    OpenApiExample("Karnataka",      value="Karnataka"),
                ],
            ),
            OpenApiParameter(
                "district",
                str,
                required=False,
                description="District name — required when field=city",
                examples=[
                    OpenApiExample("Hyderabad",      value="Hyderabad"),
                    OpenApiExample("Visakhapatnam",  value="Visakhapatnam"),
                    OpenApiExample("Bengaluru Urban", value="Bengaluru Urban"),
                ],
            ),
        ],
        examples=[
            OpenApiExample(
                "1. Get all states",
                summary="Step 1 — fetch all states",
                description="Use field=state with no other params.",
                value={"field": "state", "options": ["Andhra Pradesh", "Bihar", "Delhi", "Goa", "Gujarat", "..."]},
                response_only=True,
            ),
            OpenApiExample(
                "2. Get districts in Telangana",
                summary="Step 2 — fetch districts after selecting a state",
                description="Pass field=district and state=<selected state>.",
                value={"field": "district", "options": ["Adilabad", "Hyderabad", "Karimnagar", "Khammam", "Medchal-Malkajgiri", "Nalgonda", "Nizamabad", "Rangareddy", "Sangareddy", "Warangal Urban"]},
                response_only=True,
            ),
            OpenApiExample(
                "3. Get cities in Hyderabad district",
                summary="Step 3 — fetch cities after selecting a district",
                description="Pass field=city, state=<selected state>, district=<selected district>.",
                value={"field": "city", "options": ["Abids", "Ameerpet", "Banjara Hills", "Begumpet", "Gachibowli", "Hitec City", "Hyderabad", "Jubilee Hills", "Kondapur", "Kukatpally", "Madhapur", "Secunderabad"]},
                response_only=True,
            ),
        ],
        responses={200: {
            "type": "object",
            "properties": {
                "field":   {"type": "string", "example": "district"},
                "options": {"type": "array", "items": {"type": "string"}, "example": ["Hyderabad", "Rangareddy", "Medchal-Malkajgiri"]},
            },
        }},
        tags=["Locations"],
    )
    def get(self, request):
        field    = request.GET.get('field', '')
        state    = request.GET.get('state', '')
        district = request.GET.get('district', '')

        qs = LocationMaster.objects.all()

        if field == 'state':
            values = list(qs.values_list('state', flat=True).distinct().order_by('state'))
        elif field == 'district' and state:
            values = list(
                qs.filter(state=state)
                .exclude(district='')
                .values_list('district', flat=True)
                .distinct()
                .order_by('district')
            )
        elif field == 'city' and district:
            values = list(
                qs.filter(state=state, district=district)
                .exclude(city='')
                .values_list('city', flat=True)
                .distinct()
                .order_by('city')
            )
        else:
            values = []

        return Response({'field': field, 'options': values})
