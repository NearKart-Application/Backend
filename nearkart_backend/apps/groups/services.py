"""
NearKart — Groups Service
All business logic for group creation, membership, and product sharing.
"""
from django.db import transaction

from apps.stores.models import StoreFollow
from .models import Group, GroupMember, GroupMemberRole, GroupSharedProduct, GroupType


class GroupService:

    @staticmethod
    @transaction.atomic
    def create(name: str, created_by, group_type: str, store=None) -> Group:
        group = Group.objects.create(
            name=name,
            group_type=group_type,
            created_by=created_by,
            store=store,
        )
        GroupMember.objects.create(group=group, user=created_by, role=GroupMemberRole.ADMIN)
        return group

    @staticmethod
    def get_for_user(user):
        group_ids = GroupMember.objects.filter(user=user).values_list('group_id', flat=True)
        return Group.objects.filter(id__in=group_ids, is_active=True).select_related('created_by', 'store')

    @staticmethod
    def is_admin(group, user) -> bool:
        return GroupMember.objects.filter(
            group=group, user=user, role=GroupMemberRole.ADMIN
        ).exists()

    @staticmethod
    def is_member(group, user) -> bool:
        return GroupMember.objects.filter(group=group, user=user).exists()

    @staticmethod
    @transaction.atomic
    def add_member(group: Group, user_to_add) -> GroupMember:
        if group.group_type == GroupType.VENDOR and group.store:
            if not StoreFollow.objects.filter(store=group.store, user=user_to_add).exists():
                raise PermissionError('User does not follow this store.')

        member, created = GroupMember.objects.get_or_create(
            group=group,
            user=user_to_add,
            defaults={'role': GroupMemberRole.MEMBER},
        )
        if not created:
            raise ValueError('User is already a member of this group.')
        return member

    @staticmethod
    def remove_member(group: Group, user_to_remove):
        member = GroupMember.objects.filter(group=group, user=user_to_remove).first()
        if not member:
            raise ValueError('User is not a member of this group.')
        if group.created_by_id == user_to_remove.id:
            raise PermissionError('Cannot remove the group creator.')
        member.delete()

    @staticmethod
    def leave(group: Group, user):
        member = GroupMember.objects.filter(group=group, user=user).first()
        if not member:
            raise ValueError('You are not a member of this group.')
        if group.created_by_id == user.id:
            raise PermissionError('Group creator cannot leave. Delete the group instead.')
        member.delete()

    @staticmethod
    def make_admin(group: Group, user_to_promote):
        member = GroupMember.objects.filter(group=group, user=user_to_promote).first()
        if not member:
            raise ValueError('User is not a member of this group.')
        if member.role == GroupMemberRole.ADMIN:
            raise ValueError('User is already an admin.')
        member.role = GroupMemberRole.ADMIN
        member.save(update_fields=['role', 'updated_at'])
        return member

    @staticmethod
    def remove_admin(group: Group, user_to_demote):
        if group.created_by_id == user_to_demote.id:
            raise PermissionError('Cannot remove admin role from the group creator.')
        member = GroupMember.objects.filter(group=group, user=user_to_demote).first()
        if not member:
            raise ValueError('User is not a member of this group.')
        if member.role != GroupMemberRole.ADMIN:
            raise ValueError('User is not an admin.')
        member.role = GroupMemberRole.MEMBER
        member.save(update_fields=['role', 'updated_at'])
        return member

    @staticmethod
    def get_eligible_members(group: Group):
        """Returns store followers who are not yet group members (vendor groups only)."""
        existing_ids = GroupMember.objects.filter(group=group).values_list('user_id', flat=True)
        followers = StoreFollow.objects.filter(
            store=group.store
        ).exclude(
            user_id__in=existing_ids
        ).select_related('user')
        return [
            {'user_id': f.user.id, 'profile_id': f.user.profile_id, 'full_name': f.user.full_name}
            for f in followers
        ]

    @staticmethod
    def share_product(group: Group, product, shared_by, note: str = '') -> GroupSharedProduct:
        return GroupSharedProduct.objects.create(
            group=group, product=product, shared_by=shared_by, note=note,
        )

    @staticmethod
    def finalize_product(shared_product: GroupSharedProduct, finalized_by) -> GroupSharedProduct:
        shared_product.is_finalized = True
        shared_product.finalized_by = finalized_by
        shared_product.save(update_fields=['is_finalized', 'finalized_by', 'updated_at'])
        return shared_product

    @staticmethod
    def get_shared_products(group: Group):
        return (
            GroupSharedProduct.objects
            .filter(group=group)
            .select_related('product', 'product__store', 'shared_by', 'finalized_by')
            .order_by('-is_finalized', '-created_at')
        )
