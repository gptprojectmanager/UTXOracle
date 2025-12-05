# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

UTXOracle is a Bitcoin-native, exchange-free price oracle that calculates BTC/USD prices directly from blockchain data using statistical clustering—no external exchange APIs.

**Key Principles**: Pure Python (stdlib only), single-file reference impl, Bitcoin Core RPC only, privacy-first.

**Philosophy**: KISS + YAGNI → See [Development Principles](#development-principles)

## Running UTXOracle

```bash
python3 UTXOracle.py                    # Yesterday's price (default)
python3 UTXOracle.py -d 2025/10/15      # Specific date
python3 UTXOracle.py -rb                # Recent 144 blocks
python3 UTXOracle.py -p /path/to/data   # Custom Bitcoin data dir
python3 UTXOracle.py -h                 # Help

# Batch processing
python3 scripts/utxoracle_batch.py 2025/10/01 2025/10/10 /home/sam/.bitcoin 12
```

**Requirements**: Python 3.8+, Bitcoin Core (fully synced, RPC enabled)

## Architecture (spec-003: Hybrid)

**4-Layer Architecture**:

1. **UTXOracle.py** - Reference implementation (12-step algorithm). **IMMUTABLE**.
2. **UTXOracle_library.py** - Reusable core algorithm (Steps 5-11). API: `UTXOracleCalculator.calculate_price_for_transactions(txs)`
3. **Self-hosted Infrastructure** - mempool.space + electrs Docker stack at `/media/sam/2TB-NVMe/prod/apps/mempool-stack/`
4. **Integration** - `scripts/daily_analysis.py` (cron), `api/main.py` (FastAPI), `frontend/comparison.html` (Plotly.js)

### Service Endpoints (Localhost)

| Service | URL | Purpose |
|---------|-----|---------|
| Bitcoin Core RPC | `localhost:8332` | Tier 3 fallback |
| electrs HTTP API | `localhost:3001` | Tier 1 primary (transactions) |
| mempool backend | `localhost:8999` | Exchange prices |
| mempool frontend | `localhost:8080` | Block explorer UI |

### 3-Tier Transaction Fetching

```python
# Tier 1 (PRIMARY): electrs HTTP API - fastest
txs = fetch_from_electrs("http://localhost:3001")
# Tier 2 (FALLBACK): mempool.space public API (disabled by default)
# Tier 3 (ULTIMATE): Bitcoin Core RPC - always available
```

### Metrics Modules

#### spec-007: On-Chain Metrics

- **Monte Carlo Signal Fusion** (`scripts/metrics/monte_carlo_fusion.py`)
  - Bootstrap sampling with 95% confidence intervals
  - Weighted fusion: 0.7×whale + 0.3×utxo signal
  - Bimodal distribution detection, BUY/SELL/HOLD action
  - Performance: <3ms per calculation

- **Active Addresses** (`scripts/metrics/active_addresses.py`)
  - Unique address counting per block (deduplicated)
  - Anomaly detection: 3-sigma from 30-day MA

- **TX Volume USD** (`scripts/metrics/tx_volume.py`)
  - Volume using UTXOracle on-chain price
  - Change output heuristic (<10% of max = change)

- **Data Models** (`scripts/models/metrics_models.py`)
  - `MonteCarloFusionResult`, `ActiveAddressesMetric`, `TxVolumeMetric`, `OnChainMetricsBundle`

- **Database**: DuckDB `metrics` table (21 columns), indexed by timestamp
- **API**: `/api/metrics/latest`

#### spec-009: Advanced Analytics (+40% signal accuracy)

- **Power Law Detector** (`scripts/metrics/power_law.py`)
  - MLE estimation: τ = 1 + n / Σ ln(x_i / x_min)
  - KS test validation, regime: ACCUMULATION (τ<1.8) | NEUTRAL | DISTRIBUTION (τ>2.2)

- **Symbolic Dynamics** (`scripts/metrics/symbolic_dynamics.py`)
  - Permutation entropy: H = -Σ(p_i × log(p_i)) / log(d!)
  - Statistical complexity via Jensen-Shannon divergence
  - Patterns: ACCUMULATION_TREND | DISTRIBUTION_TREND | CHAOTIC_TRANSITION | EDGE_OF_CHAOS

- **Fractal Dimension** (`scripts/metrics/fractal_dimension.py`)
  - Box-counting: D = lim(ε→0) log(N(ε)) / log(1/ε)
  - Structure: WHALE_DOMINATED (D<0.8) | MIXED | RETAIL_DOMINATED (D>1.2)

- **Enhanced Fusion** - 7-component weighted (vs 2 in spec-007):
  - whale 25%, utxo 15%, funding 15%, oi 10%, power_law 10%, symbolic 15%, fractal 10%
  - Auto weight renormalization when components unavailable

- **API**: `/api/metrics/advanced`

## Repository Structure

```
UTXOracle/
├── UTXOracle.py              # Reference impl (IMMUTABLE)
├── UTXOracle_library.py      # Reusable algorithm
├── api/main.py               # FastAPI REST API
├── frontend/comparison.html  # Dashboard
├── scripts/
│   ├── daily_analysis.py     # Integration service
│   ├── utxoracle_batch.py    # Batch processing
│   └── metrics/              # On-chain metrics (spec-007/009)
├── tests/                    # pytest suite
├── historical_data/          # 672 days of HTML outputs
├── archive/                  # v7, v8, v9, spec-002
├── .claude/                  # Agents, skills, hooks, prompts
└── specs/                    # Feature specifications
```

**File Placement**:
- Backend → `api/`
- Frontend → `frontend/`
- Scripts → `scripts/`
- Tests → `tests/test_<module>.py`
- Specs → `specs/<feature-id>/`

**Immutable**: `UTXOracle.py`, `UTXOracle_library.py` (refactor with tests only), `historical_data/`

## Agent & Skill Architecture

### Subagents (6)

| Agent | Responsibility |
|-------|---------------|
| bitcoin-onchain-expert | ZMQ, Bitcoin Core integration |
| transaction-processor | Binary parsing, filtering |
| mempool-analyzer | Histogram, price estimation |
| data-streamer | FastAPI WebSocket |
| visualization-renderer | Canvas 2D + Three.js |
| tdd-guard | TDD enforcement |

### Skills (4) - 60-83% token savings

| Skill | Trigger Keywords |
|-------|-----------------|
| pytest-test-generator | "generate tests" |
| github-workflow | "create PR" |
| pydantic-model-generator | "pydantic model" |
| bitcoin-rpc-connector | "bitcoin rpc" |

## Development Principles

### KISS & YAGNI

**KISS**: Choose boring tech, avoid premature optimization, one module = one purpose, minimize deps, clear over clever.

**YAGNI**: Solve today's problem, no unused features, specific beats flexible, delete dead code, resist abstraction temptation.

**Code Reuse**: Never write custom code if >80% can be reused. Self-host over custom build.

✅ Use existing 6 agents + 4 skills, write simple Python, focus on implementation
❌ Don't create more skills "just in case", don't over-engineer, don't abstract before 3+ use cases

### Black Box Architecture (Eskil Steenberg)

- Constant velocity regardless of project size
- One module, one owner
- Everything replaceable via clean APIs
- If you don't understand a module, rewrite it without breaking others

### Code Philosophy

1. Transparency over efficiency (code for human understanding)
2. Zero dependencies (stdlib only for reference impl)
3. Reproducibility (verifiable from public blockchain)
4. Single file clarity (UTXOracle.py avoids abstraction intentionally)

## Development Workflow

### TDD Flow

1. **RED**: Write failing test → commit
2. **GREEN**: Minimal implementation to pass → commit
3. **REFACTOR**: Clean up with tests passing → commit

**Rules**:
- Never implement without failing test first
- One test at a time, smallest possible change
- Run pytest before AND after each edit
- Follow error messages literally (AttributeError → add method, AssertionError → fix logic)

**Baby Step Example**:
```python
# ❌ WRONG (too much at once):
def get_history(self):
    if not hasattr(self, 'history'):
        self.history = deque(maxlen=500)
    return list(self.history)

# ✅ CORRECT (baby steps):
# Step 1: Just stub
def get_history(self):
    pass

# Step 2: Minimal return
def get_history(self):
    return []

# Step 3: Add storage after test requires it
def get_history(self):
    if not hasattr(self, 'history'):
        self.history = []
    return self.history

# Step 4: Fix after test shows we need deque
def get_history(self):
    if not hasattr(self, 'history'):
        self.history = deque(maxlen=500)
    return list(self.history)
```

**When TDD doesn't fit**: Frontend JS, visualization, exploratory → tests after.

### When Stuck Protocol

**Max 3 attempts** per issue, then:
1. Document failure with approaches tried
2. Research alternatives (15min max)
3. Question fundamentals (right abstraction? simpler approach? YAGNI?)
4. Try different angle OR ask for help

### Decision Priority

1. Testability → 2. Simplicity → 3. Consistency → 4. Readability → 5. Reversibility

```python
# ❌ Clever but hard to test
result = reduce(lambda x,y: x|y, map(parse, data), {})

# ✅ Simple, testable, readable
result = {}
for item in data:
    parsed = parse(item)
    result.update(parsed)
```

### Error Handling

- Fail fast with descriptive messages (include context)
- Handle at appropriate level, never silently swallow
- Use `logging` not `print()`

```python
# ❌ Bad
raise ValueError("Invalid input")

# ✅ Good
raise ValueError(
    f"Bitcoin RPC connection failed: {rpc_url} "
    f"(check bitcoin.conf rpcuser/rpcpassword)"
)

# ❌ Bad
print(f"Processing block {height}")

# ✅ Good
logger.info(f"Processing block {height}", extra={"block_height": height})
```

### Test Guidelines

- Test behavior, not implementation
- One assertion per test (or closely related)
- Name: `test_<what>_<when>_<expected>`
- Use fixtures from `tests/conftest.py`
- Must be deterministic

```python
def test_histogram_removes_round_amounts_when_filtering_enabled():
    """Round BTC amounts (1.0, 5.0) should be filtered."""
    # Arrange
    histogram = {"1.0": 100, "1.23456": 50, "5.0": 200}
    # Act
    filtered = remove_round_amounts(histogram)
    # Assert
    assert "1.0" not in filtered
    assert filtered["1.23456"] == 50
```

### Important Rules

❌ **NEVER**: `--no-verify`, disable tests, commit broken code, `print()` for logging, hardcode secrets, commit without testing

✅ **ALWAYS**: Run `uv run pytest`, run `ruff check . && ruff format .`, explain WHY in commits, use `uv` not `pip`

## Pre-Commit Checklist

Before committing:
1. Remove temp files (`*.tmp`, `*.bak`, `__pycache__`)
2. Remove debug code (`print()`, `console.log`)
3. Run linter: `ruff check .`
4. Run tests: `uv run pytest`
5. Review `git status` for untracked files

**DELETE**: Temp files, cache, debug logs, unused imports, old TODOs
**KEEP**: `historical_data/`, tests, config files, `uv.lock`

### Cleanup Automation

Pre-commit hook (`.git/hooks/pre-commit`):

```bash
#!/bin/bash
echo "🧹 Running pre-commit cleanup..."

# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Check for temp files
TEMP_FILES=$(find . -name "*.tmp" -o -name "*.bak" 2>/dev/null)
if [ -n "$TEMP_FILES" ]; then
    echo "❌ Temporary files found:"
    echo "$TEMP_FILES"
    exit 1
fi

# Warn on debug code (don't block)
if git diff --cached | grep -E "(print\(|console\.log|debugger)"; then
    echo "⚠️  Debug code detected - review before committing"
fi

echo "✅ Pre-commit checks passed"
```

### Periodic Cleanup (Weekly)

```bash
# Find stale files (>2 weeks old)
find . -type f -mtime +14 -not -path "./.git/*" -not -path "./historical_data/*"

# Check for:
# - Orphaned files not referenced anywhere
# - Merged branches: git branch --merged
# - Outdated documentation
```

## Bitcoin Node Connection

Cookie auth (default) from `~/.bitcoin/.cookie` or bitcoin.conf credentials.

**Data paths**: Linux `~/.bitcoin`, macOS `~/Library/Application Support/Bitcoin`, Windows `%APPDATA%\Bitcoin`

**bitcoin.conf** (for ZMQ):
```conf
zmqpubhashtx=tcp://127.0.0.1:28332
zmqpubrawblock=tcp://127.0.0.1:28333
rpcuser=<user>
rpcpassword=<password>
```

## Historical Data

672 days (Dec 15, 2023 → Oct 17, 2025) in `historical_data/html_files/`. 99.85% success rate.

## Output

- Console: Date + price (e.g., "2025-10-15 price: $111,652")
- HTML: `UTXOracle_YYYY-MM-DD.html` (auto-opens unless `--no-browser`)

## License

Blue Oak Model License 1.0.0
