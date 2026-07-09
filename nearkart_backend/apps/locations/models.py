from django.db import models


class LocationMaster(models.Model):
    state    = models.CharField(max_length=100, db_index=True)
    district = models.CharField(max_length=100, blank=True, default='', db_index=True)
    city     = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        db_table = 'location_master'
        unique_together = [('state', 'district', 'city')]
        indexes = [models.Index(fields=['state', 'district'], name='loc_state_district_idx')]
        ordering = ['state', 'district', 'city']

    def __str__(self):
        return ' › '.join(filter(None, [self.state, self.district, self.city]))
