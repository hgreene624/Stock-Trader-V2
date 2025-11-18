# Production Trading Bot - Audit Logs Guide

## Overview

The production trading bot writes comprehensive audit logs in **JSONL (JSON Lines)** format for complete traceability of all trading activity.

## Log Files

All logs are written to `/app/logs/` inside the container, mounted to `./production/docker/logs/` on your host machine.

### Available Log Files

1. **orders.jsonl** - All order submissions
2. **trades.jsonl** - All trade executions
3. **performance.jsonl** - Performance snapshots after each cycle
4. **errors.jsonl** - All errors and exceptions
5. **production.log** - Human-readable text log (all events)

## Log Format

Each line is a complete JSON object with:
- `timestamp`: ISO 8601 timestamp (UTC)
- `event_type`: Type of event
- Additional fields specific to the event

## Examples

### Orders Log (`orders.jsonl`)

```json
{
  "timestamp": "2025-11-18T14:30:00.123456+00:00",
  "event_type": "order_submitted",
  "order_id": "abc123-def456-789",
  "symbol": "SPY",
  "side": "buy",
  "quantity": 10.0,
  "price": 666.23,
  "order_type": "market",
  "status": "accepted",
  "nav": 100000.00,
  "model": "SectorRotationModel_v1"
}
```

### Trades Log (`trades.jsonl`)

```json
{
  "timestamp": "2025-11-18T14:30:05.234567+00:00",
  "event_type": "trade_executed",
  "order_id": "abc123-def456-789",
  "symbol": "SPY",
  "side": "buy",
  "quantity": 10.0,
  "price": 666.25,
  "value": 6662.50,
  "new_position": 10.0,
  "nav": 100000.00
}
```

### Performance Log (`performance.jsonl`)

```json
{
  "timestamp": "2025-11-18T14:30:10.345678+00:00",
  "event_type": "cycle_complete",
  "nav": 106234.56,
  "cash": 43567.89,
  "positions_count": 3,
  "positions": {
    "SPY": 10.0,
    "QQQ": 5.0,
    "TLT": 15.0
  },
  "buying_power": 87123.45,
  "cycle_timestamp": "2025-11-18T14:00:00+00:00"
}
```

### Errors Log (`errors.jsonl`)

```json
{
  "timestamp": "2025-11-18T14:30:15.456789+00:00",
  "event_type": "order_error",
  "symbol": "SPY",
  "side": "buy",
  "quantity": 10.0,
  "error": "Insufficient buying power",
  "order_data": {...}
}
```

## Querying Logs with `jq`

### View all orders for a specific symbol

```bash
cat logs/orders.jsonl | jq 'select(.symbol == "SPY")'
```

### Count total orders by side

```bash
cat logs/orders.jsonl | jq -s 'group_by(.side) | map({side: .[0].side, count: length})'
```

### Calculate total traded value

```bash
cat logs/trades.jsonl | jq -s 'map(.value) | add'
```

### Show NAV progression over time

```bash
cat logs/performance.jsonl | jq -r '[.timestamp, .nav] | @csv'
```

### Find all errors

```bash
cat logs/errors.jsonl | jq -r '[.timestamp, .event_type, .error] | @tsv'
```

### Get latest performance snapshot

```bash
tail -1 logs/performance.jsonl | jq '.'
```

### Filter orders by date range

```bash
cat logs/orders.jsonl | jq 'select(.timestamp >= "2025-11-18T00:00:00" and .timestamp < "2025-11-19T00:00:00")'
```

### Calculate win rate

```bash
# Assuming trades have profit/loss data
cat logs/trades.jsonl | jq -s '
  map(select(.pnl != null)) |
  {
    total: length,
    wins: map(select(.pnl > 0)) | length,
    losses: map(select(.pnl < 0)) | length
  } |
  .win_rate = (.wins / .total * 100)
'
```

## Querying Logs with Python

```python
import json
from pathlib import Path

# Read all orders
orders = []
with open('production/docker/logs/orders.jsonl', 'r') as f:
    for line in f:
        orders.append(json.loads(line))

# Filter by symbol
spy_orders = [o for o in orders if o['symbol'] == 'SPY']

# Group by date
from collections import defaultdict
from datetime import datetime

orders_by_date = defaultdict(list)
for order in orders:
    date = datetime.fromisoformat(order['timestamp']).date()
    orders_by_date[date].append(order)

# Calculate daily metrics
for date, day_orders in sorted(orders_by_date.items()):
    total_value = sum(o['price'] * o['quantity'] for o in day_orders)
    print(f"{date}: {len(day_orders)} orders, ${total_value:,.2f} total value")
```

## Loading Logs into pandas

```python
import pandas as pd
import json

# Load orders into DataFrame
with open('production/docker/logs/orders.jsonl', 'r') as f:
    orders_df = pd.DataFrame([json.loads(line) for line in f])

# Convert timestamp to datetime
orders_df['timestamp'] = pd.to_datetime(orders_df['timestamp'])

# Group by symbol and calculate metrics
summary = orders_df.groupby('symbol').agg({
    'quantity': 'sum',
    'price': 'mean',
    'order_id': 'count'
}).rename(columns={'order_id': 'num_orders'})

print(summary)
```

## Log Rotation

The Docker compose configuration includes log rotation:
- Max file size: 10MB
- Max files: 5
- Total max: ~50MB

To manually rotate logs:

```bash
# Inside container
cd /app/logs
mv orders.jsonl orders.jsonl.1
touch orders.jsonl
```

Or use `logrotate` on the host machine.

## Compliance and Auditing

These JSONL logs provide complete audit trails for:

1. **Order Compliance**: Every order submitted with timestamp, symbol, quantity, price
2. **Trade Execution**: Actual fill prices and quantities
3. **Performance Tracking**: NAV snapshots at each cycle
4. **Error Analysis**: All failures with context
5. **Model Attribution**: Which model requested each trade

All timestamps are in UTC for consistency across timezones.

## Backup and Archival

Recommended backup strategy:

```bash
# Daily backup script
DATE=$(date +%Y%m%d)
cd production/docker/logs
tar -czf ~/backups/trading-logs-$DATE.tar.gz *.jsonl

# Keep last 30 days
find ~/backups -name "trading-logs-*.tar.gz" -mtime +30 -delete
```

## Integration with Log Aggregation

The JSONL format is compatible with:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **Datadog**
- **CloudWatch Logs Insights**
- **Grafana Loki**

Example Filebeat configuration:

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.jsonl
  json.keys_under_root: true
  json.add_error_key: true
```

## Security

**IMPORTANT**: Log files may contain sensitive information:
- Account equity and cash balances
- Trading positions and strategies
- Order IDs

Protect log files:
```bash
chmod 600 production/docker/logs/*.jsonl
```

Exclude from version control:
```bash
# Already in .gitignore
production/docker/logs/
```
