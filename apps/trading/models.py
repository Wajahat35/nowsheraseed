from django.db import models
from django.conf import settings
from decimal import Decimal

# ---------------------------------------------------------------------------
# FINANCIAL TRADING MODELS
# ---------------------------------------------------------------------------
class TradingAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('Standard', 'Standard Account'),
        ('ECN', 'ECN Account'),
        ('VIP', 'VIP Account'),
        ('Demo', 'Demo Account'),
        ('Prop Firm', 'Prop Firm / Funded Account'),
        ('Crypto Spot', 'Crypto Spot'),
        ('Futures', 'Futures / Derivatives'),
        ('Other', 'Other Account Type'),
    ]

    PLATFORM_CHOICES = [
        ('MetaTrader 4', 'MetaTrader 4 (MT4)'),
        ('MetaTrader 5', 'MetaTrader 5 (MT5)'),
        ('Binance', 'Binance'),
        ('Bybit', 'Bybit'),
        ('cTrader', 'cTrader'),
        ('TradingView', 'TradingView'),
        ('Other', 'Other Platform'),
    ]

    name = models.CharField(max_length=150, verbose_name="Account Name")
    broker_name = models.CharField(max_length=150, verbose_name="Broker / Exchange Name")
    account_number = models.CharField(max_length=100, verbose_name="Account ID / Number")
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPE_CHOICES, default='Standard')
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, default='MetaTrader 5')
    currency = models.CharField(max_length=10, default='USD')
    
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    current_equity = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    
    is_active = models.BooleanField(default=True, verbose_name="Account Active")
    opening_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.name} ({self.broker_name} - #{self.account_number})"

    def recalculate_financials(self):
        """Recalculate account balance & equity based on deposits, withdrawals, and trade P&L."""
        dep_sum = Decimal(str(self.deposits.aggregate(total=models.Sum('amount'))['total'] or '0.00'))
        wth_sum = Decimal(str(self.withdrawals.aggregate(total=models.Sum('amount'))['total'] or '0.00'))
        
        closed_trades = self.trades.filter(status='Closed')
        realized_pl = Decimal('0.00')
        for t in closed_trades:
            net_pl = Decimal(str(t.profit_loss or '0.00')) - Decimal(str(t.commission or '0.00')) - Decimal(str(t.swap_fee or '0.00'))
            realized_pl += net_pl

        open_trades = self.trades.filter(status='Open')
        unrealized_pl = Decimal('0.00')
        for t in open_trades:
            unrealized_pl += Decimal(str(t.profit_loss or '0.00'))

        init_bal = Decimal(str(self.initial_balance or '0.00'))
        self.current_balance = init_bal + dep_sum - wth_sum + realized_pl
        self.current_equity = self.current_balance + unrealized_pl
        TradingAccount.objects.filter(pk=self.pk).update(
            current_balance=self.current_balance,
            current_equity=self.current_equity
        )


class Deposit(models.Model):
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='deposits')
    deposit_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    payment_method = models.CharField(max_length=100, default='Bank Wire', help_text='e.g. Bank Wire, USDT, Crypto, Card')
    transaction_id = models.CharField(max_length=150, blank=True, null=True, verbose_name="Transaction / Ref ID")
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-deposit_date', '-id']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.account.recalculate_financials()

    def delete(self, *args, **kwargs):
        acc = self.account
        super().delete(*args, **kwargs)
        acc.recalculate_financials()

    def __str__(self):
        return f"Deposit {self.currency} {self.amount} -> {self.account.name} ({self.deposit_date})"


class Withdrawal(models.Model):
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='withdrawals')
    withdrawal_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    payment_method = models.CharField(max_length=100, default='Bank Wire')
    transaction_id = models.CharField(max_length=150, blank=True, null=True, verbose_name="Transaction / Ref ID")
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-withdrawal_date', '-id']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.account.recalculate_financials()

    def delete(self, *args, **kwargs):
        acc = self.account
        super().delete(*args, **kwargs)
        acc.recalculate_financials()

    def __str__(self):
        return f"Withdrawal {self.currency} {self.amount} <- {self.account.name} ({self.withdrawal_date})"


class Trade(models.Model):
    MARKET_TYPE_CHOICES = [
        ('Forex', 'Forex'),
        ('Crypto', 'Crypto'),
        ('Gold', 'Gold & Metals'),
        ('Indices', 'Indices'),
        ('Stocks', 'Stocks'),
        ('Commodities', 'Commodities'),
        ('Other', 'Other'),
    ]

    DIRECTION_CHOICES = [
        ('Buy', 'Buy / Long'),
        ('Sell', 'Sell / Short'),
    ]

    STATUS_CHOICES = [
        ('Open', 'Open Trade'),
        ('Closed', 'Closed Trade'),
    ]

    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='trades')
    trade_date = models.DateField()
    symbol = models.CharField(max_length=50, help_text="e.g. EURUSD, XAUUSD, BTCUSDT, US30")
    market_type = models.CharField(max_length=50, choices=MARKET_TYPE_CHOICES, default='Forex')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default='Buy')
    
    lot_size = models.DecimalField(max_digits=10, decimal_places=4, default=0.01, verbose_name="Lot Size / Quantity")
    entry_price = models.DecimalField(max_digits=14, decimal_places=5)
    exit_price = models.DecimalField(max_digits=14, decimal_places=5, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=14, decimal_places=5, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=14, decimal_places=5, null=True, blank=True)
    
    open_time = models.DateTimeField(null=True, blank=True)
    close_time = models.DateTimeField(null=True, blank=True)
    
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    swap_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    profit_loss = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Gross Profit / Loss")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Closed')
    strategy = models.CharField(max_length=150, blank=True, null=True, help_text="e.g. Trend Following, Scalping, SMC, Breakout")
    notes = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-trade_date', '-id']

    @property
    def net_profit(self):
        pl = Decimal(str(self.profit_loss or 0))
        comm = Decimal(str(self.commission or 0))
        swap = Decimal(str(self.swap_fee or 0))
        return pl - comm - swap

    @property
    def is_win(self):
        return self.status == 'Closed' and self.net_profit > 0

    @property
    def is_loss(self):
        return self.status == 'Closed' and self.net_profit < 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.account.recalculate_financials()

    def delete(self, *args, **kwargs):
        acc = self.account
        super().delete(*args, **kwargs)
        acc.recalculate_financials()

    def __str__(self):
        return f"{self.direction} {self.symbol} x {self.lot_size} @ {self.entry_price} ({self.account.name})"


# ---------------------------------------------------------------------------
# SEEDS TRADING OPERATIONAL MODELS (Sales, Purchases & Gate Pass)
# ---------------------------------------------------------------------------
class TradingSalesInvoice(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Partial', 'Partially Paid'),
        ('Unpaid', 'Unpaid'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    date = models.DateField()
    customer_name = models.CharField(max_length=150, verbose_name="Customer / Buyer Party Name")
    phone = models.CharField(max_length=30, blank=True, null=True)
    
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Total Amount (PKR)")
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Paid Amount (PKR)")
    balance_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Balance Amount (PKR)")
    
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')
    remarks = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last = TradingSalesInvoice.objects.order_by('-id').first()
            last_id = last.id if last else 0
            self.invoice_number = f"TSL-{(last_id + 1):04d}"

        tot = Decimal(str(self.total_amount or 0))
        pd = Decimal(str(self.paid_amount or 0))
        self.balance_amount = max(Decimal('0.00'), tot - pd)

        if self.balance_amount <= Decimal('0.00') and tot > 0:
            self.payment_status = 'Paid'
        elif pd > Decimal('0.00') and self.balance_amount > Decimal('0.00'):
            self.payment_status = 'Partial'
        else:
            self.payment_status = 'Unpaid'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.customer_name} (Balance: PKR {self.balance_amount})"


class TradingSalesItem(models.Model):
    invoice = models.ForeignKey(TradingSalesInvoice, on_delete=models.CASCADE, related_name='items')
    seed_name = models.CharField(max_length=150, verbose_name="Seed Variety / Item")
    bags_qty = models.IntegerField(default=1, verbose_name="Quantity / Bags")
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total Weight (KG / Maunds)")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Unit Rate (PKR)")
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Subtotal (PKR)")

    def save(self, *args, **kwargs):
        rate = Decimal(str(self.unit_price or 0))
        if self.bags_qty and self.bags_qty > 0:
            self.subtotal = Decimal(str(self.bags_qty)) * rate
        elif self.weight_kg and self.weight_kg > 0:
            self.subtotal = Decimal(str(self.weight_kg)) * rate
        else:
            self.subtotal = rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.seed_name} x {self.bags_qty} Bags (PKR {self.subtotal})"


class TradingPurchaseInvoice(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Partial', 'Partially Paid'),
        ('Unpaid', 'Unpaid'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    date = models.DateField()
    supplier_name = models.CharField(max_length=150, verbose_name="Supplier / Grower Party Name")
    phone = models.CharField(max_length=30, blank=True, null=True)
    
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Total Amount (PKR)")
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Paid Amount (PKR)")
    balance_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Balance Amount (PKR)")
    
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Unpaid')
    remarks = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last = TradingPurchaseInvoice.objects.order_by('-id').first()
            last_id = last.id if last else 0
            self.invoice_number = f"TPR-{(last_id + 1):04d}"

        tot = Decimal(str(self.total_amount or 0))
        pd = Decimal(str(self.paid_amount or 0))
        self.balance_amount = max(Decimal('0.00'), tot - pd)

        if self.balance_amount <= Decimal('0.00') and tot > 0:
            self.payment_status = 'Paid'
        elif pd > Decimal('0.00') and self.balance_amount > Decimal('0.00'):
            self.payment_status = 'Partial'
        else:
            self.payment_status = 'Unpaid'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.supplier_name} (Balance: PKR {self.balance_amount})"


class TradingPurchaseItem(models.Model):
    invoice = models.ForeignKey(TradingPurchaseInvoice, on_delete=models.CASCADE, related_name='items')
    seed_name = models.CharField(max_length=150, verbose_name="Seed Variety / Item")
    bags_qty = models.IntegerField(default=1, verbose_name="Quantity / Bags")
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total Weight (KG / Maunds)")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Unit Rate (PKR)")
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Subtotal (PKR)")

    def save(self, *args, **kwargs):
        rate = Decimal(str(self.unit_price or 0))
        if self.bags_qty and self.bags_qty > 0:
            self.subtotal = Decimal(str(self.bags_qty)) * rate
        elif self.weight_kg and self.weight_kg > 0:
            self.subtotal = Decimal(str(self.weight_kg)) * rate
        else:
            self.subtotal = rate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.seed_name} x {self.bags_qty} Bags (PKR {self.subtotal})"


class TradingGatePass(models.Model):
    PASS_TYPE_CHOICES = [
        ('Inward', 'Inward (Receipt)'),
        ('Outward', 'Outward (Dispatch)'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending Inspection'),
        ('Approved', 'Approved'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    pass_number = models.CharField(max_length=50, unique=True, editable=False)
    pass_type = models.CharField(max_length=20, choices=PASS_TYPE_CHOICES, default='Inward')
    date = models.DateField()
    
    vehicle_no = models.CharField(max_length=50, verbose_name="Vehicle / Truck No.")
    driver_name = models.CharField(max_length=100, blank=True, null=True)
    party_name = models.CharField(max_length=150, verbose_name="Party / Customer / Supplier Name")
    seed_item = models.CharField(max_length=150, verbose_name="Seed Variety / Lot Description")
    
    bags_qty = models.IntegerField(default=0, verbose_name="Number of Bags")
    gross_weight = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Gross Weight (KG)")
    tare_weight = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Tare Weight (KG)")
    net_weight = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Net Weight (KG)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Completed')
    remarks = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']

    def save(self, *args, **kwargs):
        if not self.pass_number:
            last = TradingGatePass.objects.order_by('-id').first()
            last_id = last.id if last else 0
            self.pass_number = f"TGP-{(last_id + 1):04d}"

        gross = Decimal(str(self.gross_weight or 0))
        tare = Decimal(str(self.tare_weight or 0))
        if gross > 0 and tare > 0:
            self.net_weight = max(Decimal('0.00'), gross - tare)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pass_number} ({self.pass_type}) - {self.vehicle_no} [{self.seed_item}]"
