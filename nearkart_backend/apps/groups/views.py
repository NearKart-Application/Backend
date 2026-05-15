"""
NearKart — Groups Views
Customer groups (open) and Vendor groups (followers-only).
"""
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample
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
)

logger = logging.getLogger(__name__)
_TAG = 'Groups'


class GroupCreateListView(APIView):
    """POST /groups/ — create | GET /groups/ — list my groups."""
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
    """GET /groups/<id>/ — detail with members | DELETE — delete group."""
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
        description='Permanently deactivates the group. Only the group creator (admin) can do this.',
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
    """POST /groups/<id>/members/add/ — add a member by phone number."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Add member',
        description=(
            'Admin adds a member by phone number. '
            'For vendor groups, the user must follow the store. '
            'For customer groups, the user just needs a NearKart account.'
        ),
        request=AddMemberSerializer,
        responses={201: OpenApiTypes.OBJECT},
        examples=[
            OpenApiExample('Add friend', value={'phone_number': '+919876543210'}, request_only=True),
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

        try:
            user_to_add = User.objects.get(phone_number=ser.validated_data['phone_number'], is_active=True)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'No active user found with this phone number.'}, status=404)

        try:
            GroupService.add_member(group, user_to_add)
        except PermissionError as e:
            return Response({'error': 'forbidden', 'message': str(e)}, status=403)
        except ValueError as e:
            return Response({'error': 'already_member', 'message': str(e)}, status=400)

        logger.info(f'[groups] user {user_to_add.id} added to group {group.id} by {request.user.id}')
        return Response({'message': f'{user_to_add.full_name or user_to_add.phone_number} added to group.'}, status=201)


class GroupRemoveMemberView(APIView):
    """DELETE /groups/<id>/members/<user_id>/remove/ — admin removes a member."""
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
    """POST /groups/<id>/leave/ — member leaves the group."""
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


class GroupProductListView(APIView):
    """GET /groups/<id>/products/ | POST — share a product."""
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
        description='Any group member can share a product by product_id. The product must be active.',
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
    """POST /groups/<id>/products/<sp_id>/finalize/ — admin finalizes a shared product."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Finalize shared product',
        description='Group admin marks a shared product as finalized (the group\'s final choice).',
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
