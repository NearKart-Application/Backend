"""
NearKart — Groups Models
Customer groups for sharing products with friends.
Vendor groups restricted to store followers only.
"""
from django.db import models
from django.conf import settings

from core.models import BaseModel
from apps.stores.models import Store
from apps.products.models import Product


class GroupType(models.TextChoices):
    CUSTOMER = 'customer', 'Customer Group'
    VENDOR   = 'vendor',   'Vendor Group'


class GroupMemberRole(models.TextChoices):
    ADMIN  = 'admin',  'Admin'
    MEMBER = 'member', 'Member'


class Group(BaseModel):
    name        = models.CharField(max_length=200)
    group_type  = models.CharField(max_length=10, choices=GroupType.choices, default=GroupType.CUSTOMER, db_index=True)
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_groups')
    store       = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='vendor_groups', null=True, blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table = 'groups'
        indexes  = [
            models.Index(fields=['created_by', 'is_active'], name='grp_creator_active_idx'),
        ]

    def __str__(self):
        return f'{self.name} ({self.group_type})'


class GroupMember(BaseModel):
    group   = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_memberships')
    role    = models.CharField(max_length=10, choices=GroupMemberRole.choices, default=GroupMemberRole.MEMBER)

    class Meta:
        db_table        = 'group_members'
        unique_together = [('group', 'user')]
        indexes         = [
            models.Index(fields=['user', 'group'], name='grp_member_user_idx'),
        ]

    def __str__(self):
        return f'{self.user} in {self.group} ({self.role})'


class GroupMessage(BaseModel):
    group   = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    sender  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_messages')
    content = models.TextField()

    class Meta:
        db_table = 'group_messages'
        ordering = ['created_at']
        indexes  = [
            models.Index(fields=['group', 'created_at'], name='grp_msg_group_time_idx'),
        ]

    def __str__(self):
        return f'{self.sender.full_name} in {self.group.name}: {self.content[:40]}'


class GroupSharedProduct(BaseModel):
    group        = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='shared_products')
    product      = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='group_shares')
    shared_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_shared_products')
    note         = models.TextField(blank=True)
    is_finalized = models.BooleanField(default=False, db_index=True)
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='finalized_products'
    )

    class Meta:
        db_table = 'group_shared_products'
        indexes  = [
            models.Index(fields=['group', 'is_finalized'], name='grp_prod_finalized_idx'),
        ]

    def __str__(self):
        return f'{self.product.name} in {self.group.name}'
