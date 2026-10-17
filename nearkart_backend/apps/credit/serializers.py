from rest_framework import serializers
from .models import CustomerCreditAccount, CreditTransaction


class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CreditTransaction
        fields = ['id', 'transaction_type', 'amount', 'note', 'payment_method', 'created_at']
        read_only_fields = ['id', 'created_at']


class CustomerCreditAccountSerializer(serializers.ModelSerializer):
    balance          = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    available_credit = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    days_oldest_unpaid = serializers.IntegerField(read_only=True)
    last_transaction = serializers.SerializerMethodField()

    class Meta:
        model  = CustomerCreditAccount
        fields = [
            'id', 'name', 'phone', 'credit_limit', 'notes', 'is_active',
            'balance', 'available_credit', 'days_oldest_unpaid', 'last_transaction',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_last_transaction(self, obj):
        tx = obj.transactions.first()
        if not tx:
            return None
        return {'type': tx.transaction_type, 'amount': str(tx.amount), 'date': tx.created_at.isoformat()}


class CustomerCreditAccountDetailSerializer(CustomerCreditAccountSerializer):
    transactions = CreditTransactionSerializer(many=True, read_only=True)

    class Meta(CustomerCreditAccountSerializer.Meta):
        fields = CustomerCreditAccountSerializer.Meta.fields + ['transactions']
