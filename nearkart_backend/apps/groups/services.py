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
    def add_member(group: Group, user_to_add, added_by=None) -> GroupMember:
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

        from apps.notifications.services import NotificationService
        adder_name = (added_by.full_name or added_by.profile_id) if added_by else 'An admin'
        NotificationService.notify_group_added(user_to_add, group.name, str(group.id), adder_name)
        return member

    @staticmethod
    def remove_member(group: Group, user_to_remove):
        member = GroupMember.objects.filter(group=group, user=user_to_remove).first()
        if not member:
            raise ValueError('User is not a member of this group.')
        if group.created_by_id == user_to_remove.id:
            raise PermissionError('Cannot remove the group creator.')
        member.delete()
        from apps.notifications.services import NotificationService
        NotificationService.notify_group_removed(user_to_remove, group.name, str(group.id))

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
        from apps.notifications.services import NotificationService
        NotificationService.notify_group_admin_promoted(user_to_promote, group.name, str(group.id))
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
        shared = GroupSharedProduct.objects.create(
            group=group, product=product, shared_by=shared_by, note=note,
        )
        from apps.notifications.services import NotificationService
        other_members = list(
            GroupMember.objects.filter(group=group).exclude(user=shared_by).select_related('user')
        )
        NotificationService.notify_group_product_shared(
            [m.user for m in other_members],
            group.name,
            str(group.id),
            shared_by.full_name or shared_by.profile_id,
            product.name,
        )
        return shared

    @staticmethod
    def finalize_product(shared_product: GroupSharedProduct, finalized_by) -> GroupSharedProduct:
        shared_product.is_finalized = True
        shared_product.finalized_by = finalized_by
        shared_product.save(update_fields=['is_finalized', 'finalized_by', 'updated_at'])
        from apps.notifications.services import NotificationService
        grp = shared_product.group
        all_members = list(GroupMember.objects.filter(group=grp).select_related('user'))
        NotificationService.notify_group_product_finalized(
            [m.user for m in all_members],
            grp.name,
            str(grp.id),
            shared_product.product.name,
        )
        try:
            vendor = shared_product.product.store.owner
            NotificationService.notify_reservation_created(
                vendor=vendor,
                customer_name=grp.name,
                reservation_id=str(grp.id),
                product_name=shared_product.product.name,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                '[groups] failed to notify vendor for finalized product %s',
                shared_product.product_id,
            )
        return shared_product

    @staticmethod
    def get_shared_products(group: Group):
        return (
            GroupSharedProduct.objects
            .filter(group=group)
            .select_related('product', 'product__store', 'shared_by', 'finalized_by')
            .order_by('-is_finalized', '-created_at')
        )
