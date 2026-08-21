from decimal import Decimal
from django.db.models import Sum, Count, Q
from .models import TradingAccount, Deposit, Withdrawal, Trade

def calculate_trading_stats(account_id=None, date_from=None, date_to=None, market_type=None, symbol=None, direction=None, status=None):
    """
    Consolidated Trading Performance Calculation Engine.
    Calculates exact totals, Win Rate %, Loss Rate %, Net P&L, Deposits & Withdrawals.
    """
    accounts_qs = TradingAccount.objects.filter(is_active=True)
    if account_id:
        accounts_qs = accounts_qs.filter(id=account_id)

    trades_qs = Trade.objects.all()
    deposits_qs = Deposit.objects.all()
    withdrawals_qs = Withdrawal.objects.all()

    if account_id:
        trades_qs = trades_qs.filter(account_id=account_id)
        deposits_qs = deposits_qs.filter(account_id=account_id)
        withdrawals_qs = withdrawals_qs.filter(account_id=account_id)

    if date_from:
        trades_qs = trades_qs.filter(trade_date__gte=date_from)
        deposits_qs = deposits_qs.filter(deposit_date__gte=date_from)
        withdrawals_qs = withdrawals_qs.filter(withdrawal_date__gte=date_from)

    if date_to:
        trades_qs = trades_qs.filter(trade_date__lte=date_to)
        deposits_qs = deposits_qs.filter(deposit_date__lte=date_to)
        withdrawals_qs = withdrawals_qs.filter(withdrawal_date__lte=date_to)

    if market_type:
        trades_qs = trades_qs.filter(market_type=market_type)
    if symbol:
        trades_qs = trades_qs.filter(symbol__icontains=symbol)
    if direction:
        trades_qs = trades_qs.filter(direction=direction)
    if status:
        trades_qs = trades_qs.filter(status=status)

    total_accounts = accounts_qs.count()
    total_balance = sum(acc.current_balance for acc in accounts_qs)
    total_equity = sum(acc.current_equity for acc in accounts_qs)

    total_deposits = deposits_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    total_withdrawals = withdrawals_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    total_trades_count = trades_qs.count()
    closed_trades = trades_qs.filter(status='Closed')
    open_trades_count = trades_qs.filter(status='Open').count()
    closed_trades_count = closed_trades.count()

    total_profit = Decimal('0.00')
    total_loss = Decimal('0.00')
    winning_count = 0
    losing_count = 0
    break_even_count = 0
    best_trade_val = Decimal('0.00')
    worst_trade_val = Decimal('0.00')

    for t in closed_trades:
        net = t.net_profit
        if net > 0:
            winning_count += 1
            total_profit += net
            if net > best_trade_val:
                best_trade_val = net
        elif net < 0:
            losing_count += 1
            total_loss += abs(net)
            if net < worst_trade_val:
                worst_trade_val = net
        else:
            break_even_count += 1

    net_pl = total_profit - total_loss

    win_rate = (winning_count / closed_trades_count * 100) if closed_trades_count > 0 else 0.0
    loss_rate = (losing_count / closed_trades_count * 100) if closed_trades_count > 0 else 0.0

    return {
        'total_accounts': total_accounts,
        'total_balance': total_balance,
        'total_equity': total_equity,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'total_trades': total_trades_count,
        'closed_trades_count': closed_trades_count,
        'open_trades_count': open_trades_count,
        'winning_trades_count': winning_count,
        'losing_trades_count': losing_count,
        'break_even_trades_count': break_even_count,
        'total_profit': total_profit,
        'total_loss': total_loss,
        'net_profit_loss': net_pl,
        'win_rate': round(win_rate, 2),
        'loss_rate': round(loss_rate, 2),
        'best_trade': best_trade_val,
        'worst_trade': worst_trade_val,
    }
