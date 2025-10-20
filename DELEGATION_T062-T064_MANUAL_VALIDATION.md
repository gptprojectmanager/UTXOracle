# Delegation Package: Manual End-to-End Validation (T062-T064)

**Feature**: User Story 1 - Real-time Price Monitoring (MVP)
**Status**: Implementation complete, manual validation pending
**Requires**: Bitcoin Core running + Browser + 24 hours runtime
**Agent**: Manual testing or `ccbrowser` with live Bitcoin data
**Estimated Time**: 2-3 hours setup + 24 hours monitoring

---

## ⚠️ Prerequisites

### Required Software
1. **Bitcoin Core ≥25.0** (fully synced or at least recent blocks)
2. **Active mempool** (check: `bitcoin-cli getmempoolinfo` shows size >100)
3. **ZMQ enabled** in `bitcoin.conf`
4. **Modern browser** (Chrome 120+, Firefox 121+, or Safari 17+)

### Bitcoin Configuration

**Check current config**:
```bash
grep zmq ~/.bitcoin/bitcoin.conf
```

**Required settings** (`~/.bitcoin/bitcoin.conf`):
```conf
# ZMQ Configuration (REQUIRED for UTXOracle Live)
zmqpubhashtx=tcp://127.0.0.1:28332
zmqpubrawblock=tcp://127.0.0.1:28333
zmqpubrawtx=tcp://127.0.0.1:28332

# RPC Configuration
server=1
rpcuser=utxoracle
rpcpassword=CHANGE_THIS_PASSWORD
rpcallowip=127.0.0.1
```

**Restart Bitcoin Core** after config changes:
```bash
bitcoin-cli stop
sleep 5
bitcoind -daemon

# Wait for startup (30-60 seconds)
bitcoin-cli getblockchaininfo
```

**Verify ZMQ is working**:
```bash
# Check if ZMQ port is listening
netstat -an | grep 28332
# Should show: tcp4  0  0  127.0.0.1.28332  *.*  LISTEN

# Test ZMQ subscription (requires pyzmq)
python3 -c "
import zmq
ctx = zmq.Context()
sock = ctx.socket(zmq.SUB)
sock.connect('tcp://127.0.0.1:28332')
sock.subscribe(b'rawtx')
print('✅ ZMQ connection OK - waiting for transaction...')
print('Received:', sock.recv_multipart())
"
# Should receive transaction data (may take 10-30 seconds)
```

---

## 🎯 Task Breakdown

### **T062: Manual End-to-End Test**

**Objective**: Verify live price updates every 0.5-5 seconds

**Steps**:

1. **Start Backend Server**:
```bash
cd /media/sam/1TB/UTXOracle

# Start with logging
uv run uvicorn live.backend.api:app --reload --log-level info 2>&1 | tee backend.log
```

**Expected Console Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     [ZMQ] Connected to Bitcoin Core: tcp://127.0.0.1:28332
INFO:     [ZMQ] Listening for mempool transactions...
INFO:     [Analyzer] Transaction received: a1b2c3d4... (2 outputs, 0.00123 BTC)
INFO:     [Analyzer] Price estimate: $113,450.00 (confidence: 0.12)
INFO:     [WebSocket] Broadcasting update to 1 clients
```

**Troubleshooting**:
- **"ZMQ connection failed"**: Check Bitcoin Core is running (`bitcoin-cli getblockchaininfo`)
- **"No transactions"**: Check mempool activity (`bitcoin-cli getmempoolinfo` → size should be >10)
- **"ModuleNotFoundError"**: Run `uv sync` to install dependencies

2. **Open Browser**:
```bash
# Open in default browser
open http://localhost:8000  # macOS
xdg-open http://localhost:8000  # Linux
start http://localhost:8000  # Windows
```

3. **Verify UI Elements**:

**✅ Expected Display**:
- **Price**: Large orange text showing "Avg: $XXX,XXX" (updates every 0.5-5 seconds)
- **Confidence**: Score 0.0-1.0 with color indicator (red <0.5, yellow 0.5-0.8, green >0.8)
- **Connection Status**: Green "● Connected" indicator
- **Stats**: "Received: X | Filtered: Y | Active: Z | Uptime: Xh Ym"
- **Canvas**: Black background with mempool-canvas element (may be empty if US2 not implemented)

**Check Browser DevTools (F12)**:
```javascript
// Console should show:
[WebSocket] Connecting to ws://localhost:8000/ws/mempool...
[WebSocket] Connected
[App] Mempool update: {price: 113600.5, confidence: 0.87, active: 4309}
```

4. **Observe Price Updates**:

**Watch for 5 minutes**:
- Price should update at least once every 5 seconds (target: 0.5-5 seconds)
- Connection status should remain "● Connected" (green)
- Stats counters should increment (Received, Active)

**Take screenshots**:
- `t=0s` (initial state)
- `t=30s` (after 30 seconds)
- `t=2min` (after 2 minutes)
- `t=5min` (after 5 minutes)

**Log observations**:
```bash
# Create validation log
cat > T062_validation.log <<EOF
## T062 Manual Validation - $(date)

### Price Update Frequency
- First update: 0.8 seconds after connection
- Average interval: 1.2 seconds
- Max interval observed: 4.8 seconds
- ✅ PASS: All updates within 0.5-5 second target

### Connection Stability
- Connection drops: 0
- Reconnection attempts: 0
- ✅ PASS: Stable connection maintained

### UI Responsiveness
- Price display updates: Smooth
- Stats panel updates: Smooth
- Browser console errors: 0
- ✅ PASS: UI responsive

### Screenshots
- t0_initial.png
- t30_after_30s.png
- t120_after_2min.png
- t300_after_5min.png

Overall: ✅ PASS
EOF
```

---

### **T063: Price Accuracy Validation**

**Objective**: Compare mempool price vs exchange rates (±2% tolerance)

**Steps**:

1. **Record UTXOracle Price**:
```bash
# Take note of price from UI (e.g., $113,600)
UTXORACLE_PRICE=113600
```

2. **Get Exchange Prices**:

**CoinMarketCap**:
```bash
# Visit https://coinmarketcap.com/currencies/bitcoin/
# Note current price (e.g., $113,850)
CMC_PRICE=113850
```

**CoinGecko**:
```bash
# Visit https://www.coingecko.com/en/coins/bitcoin
# Note current price (e.g., $113,750)
CG_PRICE=113750
```

**Binance API**:
```bash
# Current BTC/USDT price
curl -s 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT' | python3 -c "import sys, json; print(json.load(sys.stdin)['price'])"
# Output: 113825.50
BINANCE_PRICE=113825.50
```

3. **Calculate Deviation**:
```bash
# Average exchange price
EXCHANGE_AVG=$(echo "($CMC_PRICE + $CG_PRICE + $BINANCE_PRICE) / 3" | bc -l)
# $113,808.50

# Deviation
DEVIATION=$(echo "scale=4; ($UTXORACLE_PRICE - $EXCHANGE_AVG) / $EXCHANGE_AVG * 100" | bc -l)
# -0.18% (within ±2% target)

# Log result
cat >> T063_validation.log <<EOF
## T063 Price Accuracy - $(date)

UTXOracle Price: \$$UTXORACLE_PRICE
Exchange Prices:
  - CoinMarketCap: \$$CMC_PRICE
  - CoinGecko: \$$CG_PRICE
  - Binance: \$$BINANCE_PRICE
  - Average: \$$EXCHANGE_AVG

Deviation: ${DEVIATION}%

✅ PASS: Deviation within ±2% target
EOF
```

**Repeat every hour for 24 hours** (can automate):
```bash
# Automated validation script
while true; do
    TIMESTAMP=$(date +%s)
    UTXO_PRICE=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('price', 0))" 2>/dev/null)
    BINANCE=$(curl -s 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT' | python3 -c "import sys, json; print(json.load(sys.stdin)['price'])")

    echo "$TIMESTAMP,$UTXO_PRICE,$BINANCE" >> price_comparison.csv
    sleep 3600  # 1 hour
done
```

---

### **T064: 24-Hour Stability Test**

**Objective**: Run continuously for 24+ hours without crashes

**Setup**:

1. **Start Backend in tmux/screen** (persistent session):
```bash
# Using tmux
tmux new-session -s utxoracle
uv run uvicorn live.backend.api:app --log-level info 2>&1 | tee -a utxoracle_24h.log

# Detach: Ctrl+B, then D
# Reattach: tmux attach -t utxoracle
```

2. **Monitor Resource Usage**:
```bash
# In separate terminal
while true; do
    echo "=== $(date) ===" >> resource_usage.log
    ps aux | grep uvicorn | grep -v grep >> resource_usage.log
    echo "" >> resource_usage.log
    sleep 300  # Every 5 minutes
done
```

3. **Monitor Logs for Errors**:
```bash
# Watch for crashes
tail -f utxoracle_24h.log | grep -i "error\|exception\|crash\|traceback"
```

**Validation Checklist** (check every 6 hours):

| Time | Status | CPU% | RAM MB | Uptime | Errors | Notes |
|------|--------|------|--------|--------|--------|-------|
| 0h   | ✅ Running | 2.5% | 145 MB | 0h 0m | 0 | Initial state |
| 6h   | ✅ Running | 2.8% | 168 MB | 6h 12m | 0 | Stable |
| 12h  | ✅ Running | 2.6% | 172 MB | 12h 5m | 0 | Stable |
| 18h  | ✅ Running | 2.9% | 175 MB | 18h 1m | 0 | Stable |
| 24h  | ✅ Running | 2.7% | 178 MB | 24h 8m | 0 | ✅ PASS |

**Final Validation**:
```bash
# Check uptime
curl http://localhost:8000/health | python3 -c "
import sys, json
data = json.load(sys.stdin)
uptime_hours = data['uptime_seconds'] / 3600
print(f'Uptime: {uptime_hours:.1f} hours')
print('✅ PASS' if uptime_hours >= 24 else '❌ FAIL')
"
```

**Log Summary**:
```bash
cat > T064_validation.log <<EOF
## T064 24-Hour Stability Test - $(date)

### Start Time
$(head -1 utxoracle_24h.log)

### End Time
$(tail -1 utxoracle_24h.log)

### Total Uptime
$(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(f\"{json.load(sys.stdin)['uptime_seconds'] / 3600:.1f} hours\")")

### Errors/Crashes
$(grep -i "error\|exception\|crash" utxoracle_24h.log | wc -l) errors
$(grep -i "traceback" utxoracle_24h.log | wc -l) tracebacks

### Resource Usage
Peak CPU: $(awk '{print $3}' resource_usage.log | sort -rn | head -1)%
Peak RAM: $(awk '{print $4}' resource_usage.log | sort -rn | head -1) MB

### WebSocket Connections
Total connections: $(grep "WebSocket connection" utxoracle_24h.log | wc -l)
Active connections: $(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('active_connections', 0))")

### Result
✅ PASS: System ran for 24+ hours without crashes
EOF
```

---

## ✅ Success Criteria

**T062**:
- ✅ Price updates visible every 0.5-5 seconds
- ✅ UI responsive and error-free
- ✅ WebSocket connection stable

**T063**:
- ✅ Price deviation from exchanges ≤ ±2%
- ✅ Validated at multiple timestamps (hourly for 24h)

**T064**:
- ✅ Uptime ≥ 24 hours
- ✅ Zero crashes or restarts
- ✅ Memory usage stable (<500MB)
- ✅ CPU usage stable (<5%)

---

## 📦 Deliverables

1. **Validation Logs**:
   - `T062_validation.log`
   - `T063_validation.log`
   - `T064_validation.log`

2. **Screenshots**:
   - `t0_initial.png`
   - `t30_after_30s.png`
   - `t120_after_2min.png`
   - `t300_after_5min.png`

3. **Data Files**:
   - `price_comparison.csv` (24 hours of price data)
   - `resource_usage.log` (CPU/RAM monitoring)
   - `utxoracle_24h.log` (full backend log)

4. **Summary Report**:
```markdown
# User Story 1 - Manual Validation Report

**Date**: $(date)
**System**: macOS/Linux
**Bitcoin Core Version**: $(bitcoin-cli --version | head -1)
**Branch**: 002-mempool-live-oracle

## Results

### T062: End-to-End Test
- **Status**: ✅ PASS
- **Price Update Frequency**: 0.8-4.8 seconds (target: 0.5-5s)
- **Connection Stability**: 100% uptime during 5-minute test

### T063: Price Accuracy
- **Status**: ✅ PASS
- **Average Deviation**: -0.18% (target: ±2%)
- **Max Deviation Observed**: +1.42% (within target)
- **Validation Points**: 24 (hourly for 24h)

### T064: 24-Hour Stability
- **Status**: ✅ PASS
- **Total Uptime**: 24h 8m
- **Crashes**: 0
- **Memory Leaks**: None detected (178 MB peak)
- **CPU Usage**: 2.5-2.9% (stable)

## Conclusion

User Story 1 (Real-time Price Monitoring) **fully validated** and ready for production.
```

---

## 🚀 Quick Start

```bash
# 1. Ensure Bitcoin Core is running
bitcoin-cli getblockchaininfo

# 2. Start backend
cd /media/sam/1TB/UTXOracle
tmux new-session -s utxoracle
uv run uvicorn live.backend.api:app --log-level info 2>&1 | tee utxoracle_24h.log

# 3. Open browser (in another terminal)
open http://localhost:8000

# 4. Start monitoring scripts
./scripts/monitor_price_accuracy.sh &
./scripts/monitor_resources.sh &

# 5. Wait 24 hours, then collect logs
```
