from rest_framework import serializers
from .models import Expense, ExpenseCategory


class ExpenseCategorySerializer(serializers.ModelSerializer):
    expense_count = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'is_system', 'expense_count', 'created_at']
        read_only_fields = ['id', 'is_system', 'created_at']

    def get_expense_count(self, obj):
        return obj.expenses.count()


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    total_amount  = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    receipt_url   = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_name', 'amount', 'gst_amount', 'total_amount',
            'description', 'vendor_name', 'date', 'receipt_url',
            'is_recurring', 'recurrence_type', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else obj.category_name

    def get_receipt_url(self, obj):
        if obj.receipt_image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.receipt_image.url) if request else obj.receipt_image.url
        return None
