"""
NearKart — Groups Serializers
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.products.models import Product
from core.validators import validate_no_external_links
from .models import Group, GroupMember, GroupMessage, GroupSharedProduct, GroupType


class GroupCreateSerializer(serializers.Serializer):
    name       = serializers.CharField(max_length=200)
    group_type = serializers.ChoiceField(choices=GroupType.choices)

    def validate_group_type(self, value):
        request = self.context.get('request')
        if value == GroupType.VENDOR and request and request.user.role != 'vendor':
            raise serializers.ValidationError('Only vendors can create vendor groups.')
        return value


class GroupMemberSerializer(serializers.ModelSerializer):
    user_id    = serializers.UUIDField(source='user.id',         read_only=True)
    profile_id = serializers.CharField(source='user.profile_id', read_only=True)
    full_name  = serializers.CharField(source='user.full_name',  read_only=True)

    class Meta:
        model  = GroupMember
        fields = ['id', 'user_id', 'profile_id', 'full_name', 'role', 'created_at']


class GroupSerializer(serializers.ModelSerializer):
    created_by_name  = serializers.CharField(source='created_by.full_name',   read_only=True)
    created_by_profile_id = serializers.CharField(source='created_by.profile_id', read_only=True)
    store_name       = serializers.SerializerMethodField()
    member_count     = serializers.SerializerMethodField()

    class Meta:
        model  = Group
        fields = [
            'id', 'name', 'group_type', 'is_active',
            'created_by_name', 'created_by_profile_id',
            'store_name', 'member_count', 'created_at',
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_store_name(self, obj):
        return obj.store.name if obj.store else None

    @extend_schema_field(serializers.IntegerField())
    def get_member_count(self, obj):
        return obj.members.count()


class GroupDetailSerializer(GroupSerializer):
    members = GroupMemberSerializer(many=True, read_only=True)

    class Meta(GroupSerializer.Meta):
        fields = GroupSerializer.Meta.fields + ['members']


class AddMemberSerializer(serializers.Serializer):
    """
    Customer groups: provide profile_id.
    Vendor groups: provide user_id (UUID from eligible-members list).
    """
    profile_id = serializers.CharField(max_length=16, required=False, allow_blank=True)
    user_id    = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if not attrs.get('profile_id') and not attrs.get('user_id'):
            raise serializers.ValidationError('Provide either profile_id or user_id.')
        return attrs


class SharedProductSerializer(serializers.ModelSerializer):
    product_id    = serializers.UUIDField(source='product.id',         read_only=True)
    product_name  = serializers.CharField(source='product.name',       read_only=True)
    product_price = serializers.DecimalField(source='product.base_price', max_digits=10, decimal_places=2, read_only=True)
    store_name    = serializers.CharField(source='product.store.name', read_only=True)
    shared_by_name       = serializers.CharField(source='shared_by.full_name',   read_only=True)
    shared_by_profile_id = serializers.CharField(source='shared_by.profile_id',  read_only=True)
    finalized_by_name    = serializers.SerializerMethodField()

    class Meta:
        model  = GroupSharedProduct
        fields = [
            'id', 'product_id', 'product_name', 'product_price', 'store_name',
            'note', 'is_finalized', 'finalized_by_name',
            'shared_by_name', 'shared_by_profile_id', 'created_at',
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_finalized_by_name(self, obj):
        return obj.finalized_by.full_name if obj.finalized_by else None


class ShareProductSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    note       = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value, status='active', is_visible=True).exists():
            raise serializers.ValidationError('Product not found or not available.')
        return value

    def validate_note(self, value):
        return validate_no_external_links(value)


class GroupMessageSerializer(serializers.ModelSerializer):
    sender_id         = serializers.UUIDField(source='sender.id',         read_only=True)
    sender_name       = serializers.CharField(source='sender.full_name',  read_only=True)
    sender_profile_id = serializers.CharField(source='sender.profile_id', read_only=True)

    class Meta:
        model  = GroupMessage
        fields = ['id', 'sender_id', 'sender_name', 'sender_profile_id', 'content', 'created_at']


class EligibleMemberSerializer(serializers.Serializer):
    """Follower who is not yet in the group — shown in vendor eligible-members list."""
    user_id    = serializers.UUIDField()
    profile_id = serializers.CharField()
    full_name  = serializers.CharField()
