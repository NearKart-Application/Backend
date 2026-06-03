"""
NearKart — Groups Views
Customer groups (open) and Vendor groups (followers-only).
"""
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.auth_app.models import User
from apps.products.models import Product
from .models import Group, GroupSharedProduct, GroupType
from .services import GroupService
from .serializers import (
    GroupCreateSerializer,
    GroupSerializer,
    GroupDetailSerializer,
    AddMemberSerializer,
    ShareProductSerializer,
    SharedProductSerializer,
    EligibleMemberSerializer,
)

logger = logging.getLogger(__name__)
_TAG = 'Groups'


class GroupCreateListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Create group',
        description=(
            'Any user can create a customer group. '
            'Only vendors can create vendor groups (restricted to store followers).'
        ),
        request=GroupCreateSerializer,
        responses={201: GroupSerializer},
        examples=[
            OpenApiExample('Customer group', value={'name': 'Weekend Shopping', 'group_type': 'customer'}, request_only=True),
            OpenApiExample('Vendor group',   value={'name': 'VIP Followers',    'group_type': 'vendor'},   request_only=True),
        ],
    )
    def post(self, request):
        ser = GroupCreateSerializer(data=request.data, context={'request': request})
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        group_type = ser.validated_data['group_type']
        store = None
        if group_type == GroupType.VENDOR:
            try:
                store = request.user.store
            except Exception:
                return Response({'error': 'no_store', 'message': 'Create a store first.'}, status=400)

        group = GroupService.create(
            name=ser.validated_data['name'],
            created_by=request.user,
            group_type=group_type,
            store=store,
        )
        return Response(GroupSerializer(group).data, status=201)

    @extend_schema(
        tags=[_TAG],
        summary='List my groups',
        description='Returns all groups the authenticated user is a member of.',
        responses={200: GroupSerializer(many=True)},
    )
    def get(self, request):
        groups = GroupService.get_for_user(request.user)
        return Response(GroupSerializer(groups, many=True).data)


class GroupDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_group(self, group_id, user):
        try:
            group = Group.objects.select_related('created_by', 'store').get(id=group_id, is_active=True)
        except Group.DoesNotExist:
            return None
        if not GroupService.is_member(group, user):
            return None
        return group

    @extend_schema(
        tags=[_TAG],
        summary='Group detail',
        description='Returns group info with full member list. Accessible only by group members.',
        responses={200: GroupDetailSerializer},
    )
    def get(self, request, group_id):
        group = self._get_group(group_id, request.user)
        if not group:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)
        return Response(GroupDetailSerializer(group).data)

    @extend_schema(
        tags=[_TAG],
        summary='Delete group',
        description='Permanently deactivates the group. Only the group creator can do this.',
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    def delete(self, request, group_id):
        group = self._get_group(group_id, request.user)
        if not group:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)
        if group.created_by_id != request.user.id:
            return Response({'error': 'forbidden', 'message': 'Only the group creator can delete the group.'}, status=403)
        group.is_active = False
        group.save(update_fields=['is_active', 'updated_at'])
        return Response({'message': 'Group deleted.'})


class GroupAddMemberView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Add member',
        description=(
            'Admin adds a member. '
            '**Customer groups:** provide `profile_id` (e.g. NS-SF-KU-4X2B). '
            '**Vendor groups:** provide `user_id` (UUID from eligible-members list). '
            'For vendor groups, the user must follow the store.'
        ),
        request=AddMemberSerializer,
        responses={201: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample('By Profile ID (customer group)', value={'profile_id': 'NS-SF-KU-4X2B'}, request_only=True),
            OpenApiExample('By User ID (vendor group)',      value={'user_id': '{{user_id}}'},    request_only=True),
        ],
    )
    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id, is_active=True)
        except Group.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)

        if not GroupService.is_admin(group, request.user):
            return Response({'error': 'forbidden', 'message': 'Only group admin can add members.'}, status=403)

        ser = AddMemberSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        # Resolve user — by profile_id for customer groups, by user_id for vendor groups
        user_to_add = None
        if ser.validated_data.get('profile_id'):
            pid = ser.validated_data['profile_id'].strip().upper()
            try:
                user_to_add = User.objects.get(profile_id=pid, is_active=True)
            except User.DoesNotExist:
                return Response({'error': 'not_found', 'message': 'No user found with this Profile ID.'}, status=404)
        else:
            try:
                user_to_add = User.objects.get(id=ser.validated_data['user_id'], is_active=True)
            except User.DoesNotExist:
                return Response({'error': 'not_found', 'message': 'User not found.'}, status=404)

        try:
            GroupService.add_member(group, user_to_add, added_by=request.user)
        except PermissionError as e:
            return Response({'error': 'forbidden', 'message': str(e)}, status=403)
        except ValueError as e:
            return Response({'error': 'already_member', 'message': str(e)}, status=400)

        logger.info(f'[groups] user {user_to_add.id} added to group {group.id} by {request.user.id}')
        return Response({'message': f'{user_to_add.full_name or user_to_add.profile_id} added to group.'}, status=201)


class GroupRemoveMemberView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Remove member',
        description='Admin removes a member from the group. Cannot remove the group creator.',
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    def delete(self, request, group_id, user_id):
        try:
            group = Group.objects.get(id=group_id, is_active=True)
        except Group.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)

        if not GroupService.is_admin(group, request.user):
            return Response({'error': 'forbidden', 'message': 'Only group admin can remove members.'}, status=403)

        try:
            user_to_remove = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'User not found.'}, status=404)

        try:
            GroupService.remove_member(group, user_to_remove)
        except (ValueError, PermissionError) as e:
            return Response({'error': 'invalid', 'message': str(e)}, status=400)

        return Response({'message': 'Member removed.'})


class GroupLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Leave group',
        description='Leave a group. Group creator cannot leave — delete the group instead.',
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request, group_id):
        try:
            group = Group.objects.get(id=group_id, is_active=True)
        except Group.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)

        try:
            GroupService.leave(group, request.user)
        except (ValueError, PermissionError) as e:
            return Response({'error': 'invalid', 'message': str(e)}, status=400)

        return Response({'message': 'You have left the group.'})


class GroupMakeAdminView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Make member an admin',
        description='Any admin can promote another member to admin. Groups can have multiple admins.',
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request, group_id, user_id):
        try:
            group = Group.objects.get(id=group_id, is_active=True)
        except Group.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)

        if not GroupService.is_admin(group, request.user):
            return Response({'error': 'forbidden', 'message': 'Only group admin can promote members.'}, status=403)

        try:
            user_to_promote = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'User not found.'}, status=404)

        try:
            GroupService.make_admin(group, user_to_promote)
        except (ValueError, PermissionError) as e:
            return Response({'error': 'invalid', 'message': str(e)}, status=400)

        return Response({'message': f'{user_to_promote.full_name or user_to_promote.profile_id} is now an admin.'})


class GroupRemoveAdminView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Remove admin role',
        description='Demote an admin back to member. Cannot demote the group creator.',
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request, group_id, user_id):
        try:
            group = Group.objects.get(id=group_id, is_active=True)
        except Group.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)

        if not GroupService.is_admin(group, request.user):
            return Response({'error': 'forbidden', 'message': 'Only group admin can demote admins.'}, status=403)

        try:
            user_to_demote = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'User not found.'}, status=404)

        try:
            GroupService.remove_admin(group, user_to_demote)
        except (ValueError, PermissionError) as e:
            return Response({'error': 'invalid', 'message': str(e)}, status=400)

        return Response({'message': f'{user_to_demote.full_name or user_to_demote.profile_id} is no longer an admin.'})


class GroupEligibleMembersView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Eligible members (vendor groups)',
        description=(
            'Returns store followers who are not yet in the group. '
            'Only available for vendor groups. Use the returned user_id to add members.'
        ),
        responses={200: EligibleMemberSerializer(many=True)},
    )
    def get(self, request, group_id):
        try:
            group = Group.objects.select_related('store').get(id=group_id, is_active=True)
        except Group.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)

        if not GroupService.is_admin(group, request.user):
            return Response({'error': 'forbidden', 'message': 'Only group admin can view eligible members.'}, status=403)

        if group.group_type != GroupType.VENDOR:
            return Response({'error': 'invalid', 'message': 'Eligible members only available for vendor groups.'}, status=400)

        eligible = GroupService.get_eligible_members(group)
        return Response(EligibleMemberSerializer(eligible, many=True).data)


class GroupProductListView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_group(self, group_id, user):
        try:
            group = Group.objects.get(id=group_id, is_active=True)
        except Group.DoesNotExist:
            return None
        if not GroupService.is_member(group, user):
            return None
        return group

    @extend_schema(
        tags=[_TAG],
        summary='List shared products',
        description='Returns all products shared in the group. Finalized products appear first.',
        responses={200: SharedProductSerializer(many=True)},
    )
    def get(self, request, group_id):
        group = self._get_group(group_id, request.user)
        if not group:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)
        shared = GroupService.get_shared_products(group)
        return Response(SharedProductSerializer(shared, many=True).data)

    @extend_schema(
        tags=[_TAG],
        summary='Share a product',
        description=(
            'Any group member can share a product. '
            'The note must not contain external links — only NearKart app links are allowed.'
        ),
        request=ShareProductSerializer,
        responses={201: SharedProductSerializer},
        examples=[
            OpenApiExample(
                'Share with note',
                value={'product_id': '{{product_id}}', 'note': 'This looks great for the wedding!'},
                request_only=True,
            ),
        ],
    )
    def post(self, request, group_id):
        group = self._get_group(group_id, request.user)
        if not group:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)

        ser = ShareProductSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        product = Product.objects.select_related('store').get(id=ser.validated_data['product_id'])
        shared = GroupService.share_product(
            group=group,
            product=product,
            shared_by=request.user,
            note=ser.validated_data.get('note', ''),
        )
        return Response(SharedProductSerializer(shared).data, status=201)


class GroupFinalizeProductView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Finalize shared product',
        description='Group admin marks a shared product as the group\'s final choice.',
        request=None,
        responses={200: SharedProductSerializer},
    )
    def post(self, request, group_id, sp_id):
        try:
            group = Group.objects.get(id=group_id, is_active=True)
        except Group.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Group not found.'}, status=404)

        if not GroupService.is_admin(group, request.user):
            return Response({'error': 'forbidden', 'message': 'Only group admin can finalize products.'}, status=403)

        try:
            shared = GroupSharedProduct.objects.select_related(
                'product', 'product__store', 'shared_by', 'finalized_by'
            ).get(id=sp_id, group=group)
        except GroupSharedProduct.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Shared product not found.'}, status=404)

        if shared.is_finalized:
            return Response({'error': 'already_finalized', 'message': 'Product is already finalized.'}, status=400)

        shared = GroupService.finalize_product(shared, request.user)
        return Response(SharedProductSerializer(shared).data)
