from django import forms
from apps.locations.models import LocationMaster
from .models import AdminProfile


def _loc_vals(field, **filters):
    """Distinct non-empty values of `field` from LocationMaster, optionally filtered."""
    qs = LocationMaster.objects.all()
    if filters:
        qs = qs.filter(**filters)
    return list(
        qs.exclude(**{f'{field}__exact': ''})
        .values_list(field, flat=True)
        .distinct()
        .order_by(field)
    )


class AdminProfileForm(forms.ModelForm):
    """
    Custom form for AdminProfile.
    assigned_state / district / city / area are rendered as <select> dropdowns
    populated from real Store data in the DB.
    JavaScript (admin_profile_chain.js) reloads child options via AJAX when
    a parent select changes.
    """

    class Meta:
        model  = AdminProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')

        # Figure out current values (POST data takes priority over saved instance)
        cur_state    = self.data.get('assigned_state')    or (instance.assigned_state    if instance else '')
        cur_district = self.data.get('assigned_district') or (instance.assigned_district if instance else '')
        cur_city     = self.data.get('assigned_city')     or (instance.assigned_city     if instance else '')
        cur_area     = self.data.get('assigned_area')     or (instance.assigned_area     if instance else '')

        # ── State ─────────────────────────────────────────────────────
        state_vals = _loc_vals('state')
        self.fields['assigned_state'].widget = forms.Select(
            choices=[('', '— Select State —')] + [(v, v) for v in state_vals]
        )
        self.fields['assigned_state'].required = False
        self.fields['assigned_state'].label = 'State'

        # ── District ──────────────────────────────────────────────────
        district_choices = [('', '— Select District —')]
        if cur_state:
            district_choices += [(v, v) for v in _loc_vals('district', state=cur_state)]
        elif cur_district:
            district_choices += [(cur_district, cur_district)]

        self.fields['assigned_district'].widget = forms.Select(choices=district_choices)
        self.fields['assigned_district'].required = False
        self.fields['assigned_district'].label = 'District'
        self.fields['assigned_district'].help_text = 'Required for District / City / Area admins.'

        # ── City ──────────────────────────────────────────────────────
        city_choices = [('', '— Select City —')]
        if cur_district:
            city_choices += [(v, v) for v in _loc_vals('city', state=cur_state, district=cur_district)]
        elif cur_city:
            city_choices += [(cur_city, cur_city)]

        self.fields['assigned_city'].widget = forms.Select(choices=city_choices)
        self.fields['assigned_city'].required = False
        self.fields['assigned_city'].label = 'City'
        self.fields['assigned_city'].help_text = 'Required for City / Area admins.'

        # ── Area ──────────────────────────────────────────────────────
        area_choices = [('', '— Select Area / Village —')]
        if cur_city:
            area_choices += [(v, v) for v in _loc_vals('area', state=cur_state, district=cur_district, city=cur_city)]
        elif cur_area:
            area_choices += [(cur_area, cur_area)]

        self.fields['assigned_area'].widget = forms.Select(choices=area_choices)
        self.fields['assigned_area'].required = False
        self.fields['assigned_area'].label = 'Area / Village'
        self.fields['assigned_area'].help_text = 'Required for Area / Village admins.'
