# Downsampling Analysis: Phase 1 Complete

**Date**: Nov 2, 2025
**Status**: ✅ Reverse Engineering Complete (T201-T205)

---

## Executive Summary

UTXOracle.py implements **volatility-adaptive price range filtering** for HTML visualization:

- **Algorithm**: Dynamic `ax_range` (5-20%) based on price deviation
- **Typical Reduction**: ~76% data reduction for single date
- **Filtered Points**: 23k-31k points (from est. ~100k total outputs)
- **Current Behavior**: All recent dates (2025) use minimum 5% range (low volatility period)

---

## 📊 Quantitative Analysis

### Sample Measurements (5 Random Dates)

| Date | Consensus Price | Filtered Points | Price Range | ax_range | Reduction |
|------|----------------|----------------|-------------|----------|-----------|
| Oct 24, 2025 | $110,537 | 23,956 | $105k-$116k | 0.05 (5%) | ~76% |
| Oct 15, 2025 | $111,652 | 23,294 | $106k-$117k | 0.05 (5%) | ~77% |
| Oct 01, 2025 | $116,468 | 25,675 | $110k-$122k | 0.05 (5%) | ~74% |
| Sep 15, 2025 | $114,761 | 30,569 | $109k-$120k | 0.05 (5%) | ~69% |
| Aug 01, 2025 | $114,743 | 24,357 | $109k-$120k | 0.05 (5%) | ~76% |
| Jul 15, 2025 | $116,959 | 24,740 | $111k-$122k | 0.05 (5%) | ~75% |

**Average**: 25,432 filtered points, 75.5% reduction

**Assumption**: Estimated ~100k total intraday outputs (144 blocks × ~700 outputs/block)

### Key Finding

🔍 **All analyzed dates use minimum ax_range (5%)** → Current market is in **low volatility period**.

Higher volatility dates would use larger ax_range (up to 20%), resulting in MORE filtered points retained.

---

## 🔬 Algorithm Deep Dive

### Step 1: Calculate Deviation Percentage

```python
# UTXOracle.py lines 1344-1347
price_up = central_price + pct_range_med * central_price
price_dn = central_price - pct_range_med * central_price
price_range = price_up - price_dn
unused_price, av_dev = find_central_output(output_prices, price_dn, price_up)
dev_pct = av_dev / price_range
```

### Step 2: Map Deviation to Axis Range

```python
# Lines 1350-1351
map_dev_axr = (0.15 - 0.05) / (0.20 - 0.17)  # ≈ 3.333
ax_range = 0.05 + (dev_pct - 0.17) * map_dev_axr
```

**Mapping**:
- `dev_pct ≤ 0.17` → `ax_range = 0.05` (5% min)
- `dev_pct = 0.20` → `ax_range = 0.15` (15%)
- `dev_pct ≥ 0.20` → `ax_range = 0.20` (20% max, clamped)

### Step 3: Clamp Range

```python
# Lines 1354-1357
if ax_range < 0.05:
    ax_range = 0.05  # Minimum 5%
if ax_range > 0.2:
    ax_range = 0.2   # Maximum 20%
```

### Step 4: Filter Intraday Prices

```python
# Lines 1406-1411
prices = []
for i in range(len(output_prices)):
    if price_dn < output_prices[i] < price_up:  # FILTER!
        prices.append(output_prices[i])
        # Also filter: heights, timestamps, etc.
```

**Bounds Calculation**:
```python
price_up = central_price + ax_range * central_price
price_dn = central_price - ax_range * central_price
```

**Example** (Oct 24, 2025):
- Central price: $110,537
- ax_range: 0.05 (5%)
- Bounds: $104,510 - $116,564
- **Only prices within ±5% of central are kept**

---

## 🎯 Historical Series Challenge

### Current Single-Date Performance

✅ **Works well**: 100k outputs → 24k filtered points (76% reduction)

### 2023-2025 Series Challenge

❌ **Problem**: 730 dates × 24k points = **17.5M points** (still too many!)

Canvas 2D performance limit: ~1M points

**Required additional reduction**: 94.3% (17.5M → 1M)

---

## 💡 Implications for Historical Series

### Option 1: Reuse ax_range Filter (NOT sufficient alone)

```python
# Per-date filtering already done
730 dates × 24k points = 17.5M points
```

❌ **Still 17× over budget** (need <1M for Canvas 2D)

### Option 2: Additional Temporal Downsampling

**Strategy A - Fixed Sample Rate**:
```python
target_per_date = 1_000_000 / 730 ≈ 1,370 points/date
sample_rate = 1370 / 24000 ≈ 5.7% (keep 1 in 17 points)
```

**Strategy B - Temporal Aggregation**:
```python
# Aggregate into time buckets
24k points → 1.4k aggregated (min/max/avg per bucket)
Reduction: 94.3% additional
```

**Strategy C - Hybrid**:
```python
# Step 1: Per-date ax_range filter (already done)
100k → 24k (-76%)

# Step 2: Temporal aggregation
24k → 1.4k (-94.3%)

# Total: 100k → 1.4k (-98.6% total reduction)
# Series: 730 dates × 1.4k = 1.02M points ✅
```

---

## 🔍 Critical Discovery

### ⚠️ HTML Array Contains FILTERED Data, Not Final Price

**From validation tests** (Nov 2, 2025):

```javascript
// UTXOracle HTML structure
const prices = [110375.27, 110582.77, ...];  // ❌ FILTERED intraday (24k points)

ctx.fillText("UTXOracle Consensus Price $110,537", ...);  // ✅ FINAL PRICE
```

**Why this matters**:
- `prices[-1]` ≠ consensus price (Gemini's bug)
- Filtering removes points outside ±5-20% range
- Last filtered point is NOT the final convergence result

---

## 📋 Next Steps (Phase 2)

**T206-T212: Design Strategy**

Based on findings:
1. ✅ ax_range filter alone is NOT sufficient (only 76% reduction)
2. ❌ Need 98.6% total reduction for 730-date series
3. 💡 **Recommended**: Hybrid approach
   - Keep per-date ax_range filtering (already implemented)
   - Add temporal aggregation layer (new)
   - Target: 1-2k points per date

**Proposed API** (draft):
```python
# Option A: Library method
result = calculator.calculate_price_for_transactions(
    transactions,
    return_intraday=True,
    downsample_target=1500  # Target points per date
)

# Option B: Separate downsampling utility
from UTXOracle_library import downsample_for_visualization

downsampled = downsample_for_visualization(
    prices=result["intraday_prices"],
    timestamps=result["intraday_timestamps"],
    target_points=1500,
    method="temporal_aggregation"  # or "fixed_rate", "adaptive"
)
```

---

## 📚 References

- **Algorithm**: UTXOracle.py lines 1344-1411
- **Validation**: `tests/validation/README.md` (HTML price extraction bug)
- **Planning**: `docs/DOWNSAMPLING_ANALYSIS_TODO.md` (Tasks T201-T223)

---

## ✅ Tasks Complete

- [X] **T201**: Analyzed algorithm (lines 1351-1407) ✅
- [X] **T202**: Quantified reduction on 5 dates (75.5% avg) ✅
- [X] **T203**: Analyzed temporal distribution (uniform filtering by price range) ✅
- [X] **T204**: Measured downsampling (23k-31k filtered points) ✅
- [X] **T205**: Compared volatility (all recent dates = 5% min range) ✅

**Phase 1 Status**: ✅ COMPLETE

**Next**: Phase 2 Design (T206-T212) - Strategy selection for 2023-2025 series
