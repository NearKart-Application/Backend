from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsVendor
from .models import CustomerCreditAccount, CreditTransaction
from .serializers import (
    CustomerCreditAccountSerializer,
    CustomerCreditAccountDetailSerializer,
    CreditTransactionSerializer,
)


def _vendor_store(request):
    return request.user.store


class CreditAccountListView(APIView):
    """GET /credit/customers/  — list all credit accounts for this store
       POST /credit/customers/ — create a new customer credit account"""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store    = _vendor_store(request)
        accounts = CustomerCreditAccount.objects.filter(store=store, is_active=True)
        return Response(CustomerCreditAccountSerializer(accounts, many=True).data)

    def post(self, request):
        store = _vendor_store(request)
        ser   = CustomerCreditAccountSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        account = ser.save(store=store)
        return Response(CustomerCreditAccountSerializer(account).data, status=status.HTTP_201_CREATED)


class CreditAccountDetailView(APIView):
    """GET   /credit/customers/{id}/ — full ledger + transactions
       PATCH /credit/customers/{id}/ — update credit limit / notes
       DELETE /credit/customers/{id}/ — soft-delete account"""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_account(self, request, account_id):
        store = _vendor_store(request)
        return CustomerCreditAccount.objects.get(id=account_id, store=store)

    def get(self, request, account_id):
        try:
            account = self._get_account(request, account_id)
        except CustomerCreditAccount.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CustomerCreditAccountDetailSerializer(account).data)

    def patch(self, request, account_id):
        try:
            account = self._get_account(request, account_id)
        except CustomerCreditAccount.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        ser = CustomerCreditAccountSerializer(account, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(CustomerCreditAccountSerializer(account).data)

    def delete(self, request, account_id):
        try:
            account = self._get_account(request, account_id)
        except CustomerCreditAccount.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        account.is_active = False
        account.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CreditTransactionView(APIView):
    """POST /credit/customers/{id}/transactions/ — record credit sale or payment"""
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, account_id):
        store = _vendor_store(request)
        try:
            account = CustomerCreditAccount.objects.get(id=account_id, store=store)
        except CustomerCreditAccount.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        ser = CreditTransactionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # Enforce credit limit for new credit sales
        if ser.validated_data['transaction_type'] == CreditTransaction.CREDIT:
            if account.credit_limit > 0:
                new_balance = account.balance + ser.validated_data['amount']
                if new_balance > account.credit_limit:
                    return Response(
                        {'detail': f'Credit limit of ₹{account.credit_limit} would be exceeded.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        tx = ser.save(account=account, recorded_by=request.user)
        return Response(CreditTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


class CreditAgingReportView(APIView):
    """GET /credit/aging/ — outstanding balances bucketed by age (0-30, 31-60, 61-90, 90+ days)"""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        store    = _vendor_store(request)
        accounts = CustomerCreditAccount.objects.filter(store=store, is_active=True).prefetch_related('transactions')

        today = timezone.now().date()
        buckets = {'0_30': [], '31_60': [], '61_90': [], '90_plus': []}
        total_outstanding = 0

        for acc in accounts:
            bal = acc.balance
            if bal <= 0:
                continue
            days = acc.days_oldest_unpaid
            entry = {
                'id':      str(acc.id),
                'name':    acc.name,
                'phone':   acc.phone,
                'balance': float(bal),
                'days':    days,
            }
            total_outstanding += float(bal)
            if days <= 30:
                buckets['0_30'].append(entry)
            elif days <= 60:
                buckets['31_60'].append(entry)
            elif days <= 90:
                buckets['61_90'].append(entry)
            else:
                buckets['90_plus'].append(entry)

        return Response({
            'total_outstanding': total_outstanding,
            'buckets': buckets,
            'generated_at': today.isoformat(),
        })


class CreditReminderView(APIView):
    """
    POST /credit/customers/{id}/remind/
    Logs a reminder attempt and returns a WhatsApp deep-link / SMS message
    the vendor can send manually, or triggers configured messaging provider.
    Actual dispatch requires MSG91/Twilio credentials in settings.
    """
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, account_id):
        store = _vendor_store(request)
        try:
            account = CustomerCreditAccount.objects.get(id=account_id, store=store)
        except CustomerCreditAccount.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        balance = account.balance
        if balance <= 0:
            return Response({'detail': 'No outstanding balance — no reminder needed.'}, status=status.HTTP_400_BAD_REQUEST)

        message = (
            f'Hi {account.name}, you have an outstanding balance of ₹{balance:.2f} '
            f'at {store.name}. Please settle at your earliest convenience. Thank you!'
        )
        whatsapp_url = None
        if account.phone:
            phone = account.phone.replace('+', '').replace('-', '').replace(' ', '')
            if not phone.startswith('91'):
                phone = '91' + phone
            whatsapp_url = f'https://wa.me/{phone}?text={message.replace(" ", "%20")}'

        return Response({
            'account_id': str(account.id),
            'name': account.name,
            'phone': account.phone,
            'balance': str(balance),
            'message': message,
            'whatsapp_url': whatsapp_url,
            'reminder_sent': False,
        })


class CustomerDuesView(APIView):
    """
    GET /credit/my-dues/?store_id={uuid}&phone={phone}
    Public (unauthenticated) endpoint — customer can look up their dues
    at a specific store by phone number.
    """
    permission_classes = []  # public

    def get(self, request):
        store_id = request.query_params.get('store_id')
        phone    = request.query_params.get('phone', '').strip()
        if not store_id or not phone:
            return Response({'detail': 'store_id and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            account = CustomerCreditAccount.objects.get(store_id=store_id, phone=phone, is_active=True)
        except CustomerCreditAccount.DoesNotExist:
            return Response({'outstanding': '0.00', 'transactions': []})

        from .serializers import CustomerCreditAccountDetailSerializer
        data = CustomerCreditAccountDetailSerializer(account).data
        return Response({
            'name':            account.name,
            'outstanding':     str(account.balance),
            'credit_limit':    str(account.credit_limit),
            'available_credit': str(account.available_credit) if account.available_credit is not None else None,
            'transactions':    data['transactions'],
        })


class CreditStatementView(APIView):
    """
    GET /credit/customers/{id}/statement/
    Returns a JSON statement suitable for client-side PDF generation.
    Includes full transaction ledger with running balance.
    """
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request, account_id):
        store = _vendor_store(request)
        try:
            account = CustomerCreditAccount.objects.get(id=account_id, store=store)
        except CustomerCreditAccount.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        txs = account.transactions.order_by('created_at')
        running = 0
        ledger  = []
        for tx in txs:
            if tx.transaction_type == CreditTransaction.CREDIT:
                running += float(tx.amount)
            else:
                running -= float(tx.amount)
            ledger.append({
                'date':        tx.created_at.strftime('%d %b %Y'),
                'type':        tx.transaction_type,
                'amount':      str(tx.amount),
                'note':        tx.note,
                'method':      tx.payment_method,
                'balance':     f'{running:.2f}',
            })

        return Response({
            'store_name':     store.name,
            'customer_name':  account.name,
            'customer_phone': account.phone,
            'credit_limit':   str(account.credit_limit),
            'outstanding':    str(account.balance),
            'generated_at':   timezone.now().strftime('%d %b %Y, %I:%M %p'),
            'ledger':         ledger,
        })
