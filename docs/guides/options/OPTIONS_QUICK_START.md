# Options Trading - Quick Start Guide

## 🚀 When You Get Options Approval

### 1. Apply for Options Trading
1. Go to https://alpaca.markets → Account Settings
2. Click "Apply for Options Trading"
3. Fill out application (need Level 2+)
4. Wait 1-2 business days

### 2. Verify Approval
```bash
export ALPACA_API_KEY='your_key'
export ALPACA_SECRET_KEY='your_secret'

python3 -c "
from engines.options_engine import OptionsEngine
engine = OptionsEngine(paper=False)
account = engine.get_account_info()
print(f'Options Level: {account[\"options_approved_level\"]}')
print(f'Options Buying Power: \${account[\"options_buying_power\"]:,.2f}')
"
```

### 3. Run Paper Test Trade
```bash
python3 -c "
from engines.options_engine import OptionsEngine
import datetime

engine = OptionsEngine(paper=True)

# Search for SPY puts
today = datetime.date.today()
min_date = (today + datetime.timedelta(days=30)).isoformat()
max_date = (today + datetime.timedelta(days=45)).isoformat()

contracts = engine.search_contracts('SPY', min_date, max_date, 'put', limit=5)
print(contracts[['symbol', 'strike', 'dte']])

# Dry run order (safe)
if len(contracts) > 0:
    result = engine.sell_cash_secured_put(
        contracts.iloc[0]['symbol'],
        quantity=1,
        limit_price=2.50,
        dry_run=True  # Won't actually place order
    )
    print(result)
"
```

### 4. Place First Live Order (When Ready)
```bash
python3 -c "
from engines.options_engine import OptionsEngine

engine = OptionsEngine(paper=True)  # Start with paper!

# Find suitable contract
contracts = engine.search_contracts('SPY', '2025-01-15', '2025-02-15', 'put')
best_contract = contracts.iloc[0]['symbol']

# Sell cash-secured put
result = engine.sell_cash_secured_put(
    contract_symbol=best_contract,
    quantity=1,
    limit_price=2.50,
    dry_run=False  # Real order (paper account)
)

print('Order placed:', result)
"
```

### 5. Monitor Position
```bash
python3 -c "
from engines.options_engine import OptionsEngine
engine = OptionsEngine(paper=True)
positions = engine.get_positions()
print(positions[['symbol', 'strike', 'dte', 'unrealized_pl']])
"
```

### 6. Close Position (50% Profit or 21 DTE)
```bash
python3 -c "
from engines.options_engine import OptionsEngine

engine = OptionsEngine(paper=True)
positions = engine.get_positions()

# Close first position
if len(positions) > 0:
    symbol = positions.iloc[0]['symbol']
    qty = abs(positions.iloc[0]['qty'])

    result = engine.buy_to_close_put(
        contract_symbol=symbol,
        quantity=qty,
        limit_price=1.25,  # Half of entry premium
        dry_run=False
    )
    print('Closed:', result)
"
```

---

## 📊 Optimal Parameters (from testing)

```yaml
# Conservative (recommended first 30 days)
target_delta: 0.30
min_dte: 30
max_dte: 45
profit_target_pct: 0.50
time_exit_dte: 21
max_contracts: 1
allowed_regimes: [bull, neutral]

# Expected: 8-12% annual
```

---

## 🎯 Capital Requirements

| Contracts | Strike  | Required Capital | Expected Annual Return |
|-----------|---------|------------------|------------------------|
| 1         | $600    | $60,000          | $6,000 (10%)           |
| 2         | $600    | $120,000         | $12,000 (10%)          |
| 1         | $200    | $20,000          | $2,000 (10%)           |

---

## ⚠️ Key Rules

1. **Always cash-secured** - Must have strike × 100 × contracts in cash
2. **Regime filter** - Only sell in bull/neutral markets (above 200-day MA)
3. **Exit discipline** - Close at 50% profit OR 21 DTE (whichever first)
4. **Start small** - Begin with 1 contract in paper trading
5. **Track everything** - Log all trades for 30 days before going live

---

## 🔧 Emergency Stop

```bash
# Close ALL option positions immediately
python3 -c "
from engines.options_engine import OptionsEngine
engine = OptionsEngine(paper=False)  # Use your account type
positions = engine.get_positions()

for _, pos in positions.iterrows():
    if pos['type'] == 'put' and pos['qty'] < 0:
        engine.buy_to_close_put(
            pos['symbol'],
            abs(pos['qty']),
            dry_run=False  # Market order
        )
        print(f'Closed {pos[\"symbol\"]}')
"
```

---

## 📚 Full Documentation

See `OPTIONS_TRADING_GUIDE.md` for:
- Complete API reference
- Risk management details
- Troubleshooting guide
- Performance tracking
- Optimization results

---

## ✅ Pre-Launch Checklist

- [ ] Options trading approved by Alpaca
- [ ] Verified options_approved_level >= 2
- [ ] Paper traded for 30 days
- [ ] Actual returns match expectations (>10% annual)
- [ ] Win rate > 70%
- [ ] Max drawdown < 20%
- [ ] Capital available ($60K+ recommended)
- [ ] Emergency stop procedure tested

---

**Current Status:** ✅ Built and tested, awaiting Alpaca approval

**Next Step:** Apply at https://alpaca.markets → Account Settings → Options Trading
