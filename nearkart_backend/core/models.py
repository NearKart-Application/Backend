"""
NearKart — Core Base Model
All NearKart models inherit from BaseModel
"""
import uuid
from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model for all NearKart models.
    Provides UUID primary key and timestamps.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'
