# UTXOracle Live - Modular Architecture

**Objective**: Live mempool analysis using black box modules (Eskil Steenberg principles)

**Principle**: One module, one person. Everything replaceable.

**Implementation**: Python MVP → Optional Rust migration

---

## Architecture Principles (Vibe Coding)

### Core Tenets

1. **Constant developer velocity** - Fast iteration regardless of project size
2. **One module, one person** - Each module independently owned/developed
3. **Everything replaceable** - If you don't understand it, rewrite it without breaking others
4. **Black box interfaces** - Modules communicate only through clean, defined APIs
5. **Write 5 lines today** - Avoid future context switching by writing upfront, not editing later

**Reference**: [Eskil Steenberg - Architecting LARGE Software Projects](https://www.youtube.com/watch?v=sSpULGNHyoI)

### Why This Matters for AI Development

When AI generates complex code we don't understand, we can easily **replace that specific module** without touching the rest of the system. Each module is a manageable, bite-sized chunk.

**Example**: If mempool analyzer generates buggy code → rewrite just that module → system still works.

---

## System Modules (Black Boxes)

### Module 1: Bitcoin Interface

**Task File**: `docs/tasks/01_bitcoin_interface.md`

**Responsibility**: Subscribe to Bitcoin Core ZMQ, yield raw mempool transactions

**Black Box Contract**:
```python
# Input: Bitcoin Core ZMQ endpoint
# Output: AsyncGenerator[RawTransaction]
# Side Effects: None (stateless listener)

async def stream_mempool_transactions() -> AsyncGenerator[RawTransaction, None]:
    """
    Yields raw mempool transactions as they arrive.

    Raises:
        ConnectionError: If ZMQ connection fails after retries
    """
    pass
```

**Data Model**:
```python
@dataclass
class RawTransaction:
    raw_bytes: bytes
    timestamp: float
    topic: Literal['rawtx']
```

**Replaceable**: Yes (swap ZMQ for file replay, mock data, different node)

---

### Module 2: Transaction Processor

**Task File**: `docs/tasks/02_transaction_processor.md`

**Responsibility**: Parse binary tx, apply UTXOracle filters, extract amounts

**Black Box Contract**:
```python
# Input: RawTransaction
# Output: Optional[ProcessedTransaction] (None if filtered out)
# Side Effects: None (pure function)

def process_mempool_transaction(raw_tx: RawTransaction) -> Optional[ProcessedTransaction]:
    """
    Parses and filters transaction.

    Returns ProcessedTransaction if passes UTXOracle filters, None otherwise.
    """
    pass
```

**Data Model**:
```python
@dataclass
class ProcessedTransaction:
    txid: str
    amounts: List[float]       # BTC amounts (filtered outputs)
    timestamp: float
    fee_rate: Optional[float]  # sat/vB
    input_count: int
    output_count: int
```

**Replaceable**: Yes (swap filtering algorithm, parsing logic)

---

### Module 3: Mempool Analyzer

**Task File**: `docs/tasks/03_mempool_analyzer.md`

**Responsibility**: Maintain rolling histogram, estimate real-time price

**Black Box Contract**:
```python
# Input: ProcessedTransaction stream
# Output: (price, confidence_score)
# Side Effects: Maintains in-memory rolling histogram

class MempoolAnalyzer:
    def add_transaction(self, tx: ProcessedTransaction) -> None:
        """Update rolling histogram with new tx"""
        pass

    def estimate_price(self) -> Tuple[float, float]:
        """
        Returns (price, confidence_score)

        Process:
            1. Normalize histogram (Step 7)
            2. Slide stencils (Steps 8-9)
            3. Converge to exact price (Step 11)
        """
        pass
```

**Replaceable**: Yes (swap histogram logic, stencil algorithm, convergence method)

---

### Module 4: Data Streamer

**Task File**: `docs/tasks/04_data_streamer.md`

**Responsibility**: Orchestrate pipeline, stream data to browser via WebSocket

**Black Box Contract**:
```python
# Input: Orchestrates Module 1-3
# Output: WebSocket JSON stream
# Side Effects: Manages client connections

@app.websocket("/ws/mempool")
async def websocket_endpoint(websocket: WebSocket):
    """
    Streams mempool state to browser clients.

    Message format:
    {
        "price": float,
        "confidence": float,
        "transactions": List[dict],
        "stats": dict,
        "timestamp": float
    }
    """
    pass
```

**Replaceable**: Yes (swap WebSocket for SSE, gRPC, HTTP polling)

---

### Module 5: Visualization Renderer

**Task File**: `docs/tasks/05_visualization_renderer.md`

**Responsibility**: Render real-time scatter plot in browser

**Black Box Contract**:
```javascript
// Input: WebSocket JSON stream
// Output: Visual display (Canvas or WebGL)
// Side Effects: DOM manipulation

class MempoolVisualizer {
    constructor(canvasId) { /* ... */ }

    updateData(data) {
        // Receive WebSocket message
        // Update internal state
    }

    render() {
        // Draw scatter plot
        // 30fps (Canvas) or 60fps (WebGL)
    }
}
```

**Replaceable**: Yes (swap Canvas for WebGL, SVG, custom renderer)

---

## Module Communication Protocol

**Key Principle**: Modules communicate ONLY via data structures, never function calls.

```python
# shared/models.py - ONLY file shared between modules

from dataclasses import dataclass
from typing import List, Optional, Literal

@dataclass
class RawTransaction:
    """Bitcoin ZMQ raw transaction"""
    raw_bytes: bytes
    timestamp: float
    topic: Literal['rawtx']

@dataclass
class ProcessedTransaction:
    """Filtered transaction with extracted amounts"""
    txid: str
    amounts: List[float]
    timestamp: float
    fee_rate: Optional[float]
    input_count: int
    output_count: int

@dataclass
class MempoolState:
    """Current mempool analysis state"""
    price: float
    confidence: float
    active_tx_count: int
    total_received: int
    total_filtered: int
    uptime_seconds: float
```

**No cross-module dependencies**. Only data structures.

---

## Tech Stack Per Module (MVP)

### Module 1: Bitcoin Interface
```toml
[dependencies]
pyzmq = ">=25.1.1"
```

### Module 2: Transaction Processor
```toml
[dependencies]
# None - pure Python (reuses UTXOracle.py parsing functions)
```

### Module 3: Mempool Analyzer
```toml
[dependencies]
# None - pure Python (UTXOracle algorithm)
```

### Module 4: Data Streamer
```toml
[dependencies]
fastapi = ">=0.104.1"
uvicorn[standard] = ">=0.24.0"
```

### Module 5: Visualization
```html
<!-- Zero dependencies (vanilla JS + Canvas 2D) -->
<script src="mempool-viz.js"></script>

<!-- Production: Three.js from CDN -->
<script type="importmap">
{
    "imports": {
        "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"
    }
}
</script>
```

**Total Python dependencies**: 3 (pyzmq, fastapi, uvicorn)

---

## Module Testing (Independent)

```python
# tests/test_zmq_listener.py (Module 1)
@pytest.mark.asyncio
async def test_zmq_stream():
    async for raw_tx in stream_mempool_transactions():
        assert isinstance(raw_tx, RawTransaction)
        assert len(raw_tx.raw_bytes) > 0
        break  # Test first tx only

# tests/test_tx_processor.py (Module 2)
def test_filter_valid_transaction():
    raw_tx = RawTransaction(valid_tx_bytes, 1234567890.0, 'rawtx')
    result = process_mempool_transaction(raw_tx)

    assert result is not None
    assert len(result.amounts) > 0

# tests/test_mempool_analyzer.py (Module 3)
def test_price_estimation():
    analyzer = MempoolAnalyzer()

    for tx in sample_transactions:
        analyzer.add_transaction(tx)

    price, confidence = analyzer.estimate_price()
    assert 50000 < price < 200000  # Reasonable range
```

Each module testable in **complete isolation**.

---

## Agent Assignment

| Module | Agent Type | Task File | Duration |
|--------|------------|-----------|----------|
| Bitcoin Interface | `bitcoin-onchain-expert` | 01_bitcoin_interface.md | 1-2 weeks |
| Transaction Processor | `general-purpose` | 02_transaction_processor.md | 2-3 weeks |
| Mempool Analyzer | `general-purpose` | 03_mempool_analyzer.md | 3-4 weeks |
| Data Streamer | `general-purpose` | 04_data_streamer.md | 2 weeks |
| Visualization | `general-purpose` | 05_visualization_renderer.md | 2-6 weeks |

**Total**: 5 agents, each owns 1 module completely

---

## File Structure (UV Workspace)

```
UTXOracle/
├── pyproject.toml         # Workspace root
├── uv.lock                # Lockfile (commit!)
│
├── live/
│   ├── pyproject.toml     # Live system package
│   │
│   ├── backend/           # Modules 1-4
│   │   ├── zmq_listener.py      # Module 1
│   │   ├── tx_processor.py      # Module 2
│   │   ├── mempool_analyzer.py  # Module 3
│   │   ├── api.py               # Module 4
│   │   ├── orchestrator.py      # Pipeline coordinator
│   │   │
│   │   ├── histogram.py         # Module 3 internals
│   │   ├── stencil.py           #   (can rewrite these
│   │   ├── convergence.py       #    without touching
│   │   ├── bitcoin_parser.py    #    other modules)
│   │   │
│   │   ├── config.py
│   │   └── models.py
│   │
│   ├── frontend/          # Module 5
│   │   ├── index.html
│   │   ├── mempool-viz.js       # Canvas 2D (MVP)
│   │   ├── mempool-viz-webgl.js # Three.js (production)
│   │   └── styles.css
│   │
│   └── shared/
│       └── models.py      # ONLY shared file
│
└── tests/
    ├── test_zmq_listener.py
    ├── test_tx_processor.py
    ├── test_mempool_analyzer.py
    ├── test_api.py
    └── fixtures/
```

**Key**: Each module in `backend/` is independently replaceable.

---

## Module Replacement Examples

### Example 1: Swap Bitcoin Interface

```python
# Old: ZMQ real-time
async def stream_mempool_transactions():
    async for raw_tx_bytes in zmq_subscribe():
        yield RawTransaction(raw_tx_bytes, time.time(), 'rawtx')

# New: File replay (for testing)
async def stream_mempool_transactions():
    with open('mempool_recording.json') as f:
        for line in f:
            tx_data = json.loads(line)
            yield RawTransaction(bytes.fromhex(tx_data['hex']), tx_data['ts'], 'rawtx')
            await asyncio.sleep(0.1)  # Simulate real-time

# Interface unchanged → Module swapped → System works
```

### Example 2: Swap Mempool Analyzer

```python
# Old: UTXOracle algorithm (histogram + stencils)
class MempoolAnalyzer:
    def estimate_price(self):
        # 500 lines of histogram/stencil logic
        return price, confidence

# New: Simple moving average (for comparison)
class MempoolAnalyzer:
    def estimate_price(self):
        # 10 lines of simple average
        prices = [usd/amt for amt in self.recent_amounts for usd in [100, 1000]]
        return statistics.median(prices), 0.5

# Interface unchanged → Module swapped → Can A/B test algorithms
```

### Example 3: Swap Visualization

```javascript
// Old: Canvas 2D
class MempoolVisualizer {
    render() {
        ctx.clearRect(0, 0, width, height);
        for (const tx of txs) {
            ctx.fillRect(scaleX(tx.timestamp), scaleY(tx.price), 2, 2);
        }
    }
}

// New: Three.js WebGL
class MempoolVisualizer {
    render() {
        const positions = new Float32Array(txs.length * 3);
        txs.forEach((tx, i) => {
            positions[i*3] = scaleX(tx.timestamp);
            positions[i*3+1] = scaleY(tx.price);
            positions[i*3+2] = 0;
        });
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        renderer.render(scene, camera);
    }
}

// Interface unchanged → Module swapped → 60fps instead of 30fps
```

---

## Development Velocity Principles

### 1. One Person Per Module
Each agent owns one module completely. Can rewrite without affecting others.

**Example**: Agent 3 rewrites mempool analyzer from scratch → agents 1,2,4,5 unaffected.

### 2. Write 5 Lines Today (Not Edit 1 Tomorrow)
Don't edit existing code. Write new module, swap interfaces.

**Example**: Instead of debugging buggy histogram → write new simple histogram module → swap.

### 3. Black Box Everything
Modules don't know about each other's internals. Only interfaces matter.

**Example**: Analyzer doesn't care if transactions come from ZMQ or file. Just receives `ProcessedTransaction`.

### 4. Constant Velocity
Adding features = adding modules, not editing existing ones.

**Example**: Want fee market analysis? → Add new `FeeAnalyzer` module → stream alongside price.

---

## Rust Migration Path (Future)

**Motivation**: 10-100x speedup for core algorithm (histogram, stencil, convergence)

**Approach**: Replace Python modules with Rust, keep interfaces identical

### Phase 1: Benchmark Baseline
```bash
uv run python -m cProfile live/backend/mempool_analyzer.py
# Identify hotspots: histogram.py, stencil.py, convergence.py
```

### Phase 2: Rewrite in Rust
```rust
// core_rust/src/lib.rs

use pyo3::prelude::*;

#[pyclass]
pub struct Histogram {
    bins: Vec<f64>,
    counts: Vec<f64>,
}

#[pymethods]
impl Histogram {
    #[new]
    fn new() -> Self { /* ... */ }

    fn add_amount(&mut self, amount: f64) { /* ... */ }

    fn normalize(&mut self) { /* ... */ }
}

#[pymodule]
fn core_rust(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Histogram>()?;
    Ok(())
}
```

### Phase 3: Build Python Bindings
```toml
# core_rust/Cargo.toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }

[lib]
name = "core_rust"
crate-type = ["cdylib"]
```

```bash
# Build Rust module
maturin develop --release

# Use in Python (drop-in replacement)
# from core_rust import Histogram  # Rust
from histogram import Histogram    # Python (old)
```

### Phase 4: Benchmark Improvement
```python
# Should see 10-100x speedup
pytest tests/benchmark_histogram.py --rust
```

**Key**: Black box interface allows seamless swap. Other modules don't know/care if histogram is Python or Rust.

---

## TDD Guard Integration

**Recommended**: `pytest-watch` for test-driven development

```bash
# Install TDD tools
uv add --dev pytest-watch pytest-testmon pytest-cov

# Auto-run tests on file change
uv run ptw -- --testmon --cov=live/backend

# When you save zmq_listener.py:
# → Only tests for zmq_listener.py run (testmon)
# → Coverage report updates
# → Red/Green/Refactor cycle
```

**Benefits**:
- Instant feedback (tests run <1sec after save)
- Only affected tests run (testmon)
- Maintains constant developer velocity

**Workflow**:
```bash
# Terminal 1: Run tests continuously
uv run ptw -- --testmon

# Terminal 2: Edit code
vim live/backend/zmq_listener.py

# Terminal 1: Auto-updates with test results
# PASSED tests/test_zmq_listener.py::test_connect
```

---

## ccundo Integration (Undo System)

**Path**: `/media/sam/1TB/ccundo` (approved tool)

**Use Case**: Checkpoint before agent implements module, rollback if buggy

```bash
# Before launching agent for Task 01
ccundo checkpoint "before-task-01-bitcoin-interface"

# Launch agent, agent implements Module 1
# ... agent creates live/backend/zmq_listener.py ...

# Test module
uv run pytest tests/test_zmq_listener.py

# If tests fail:
ccundo rollback "before-task-01-bitcoin-interface"

# If tests pass:
ccundo checkpoint "after-task-01-completed"
```

**Benefits**:
- Safe experimentation with AI-generated code
- Easy rollback if module doesn't work
- Preview changes before committing

**Commands**:
```bash
ccundo checkpoint <name>     # Save current state
ccundo preview <name>        # Preview changes since checkpoint
ccundo rollback <name>       # Revert to checkpoint
ccundo list                  # Show all checkpoints
```

---

## Success Criteria

✅ Each module runs independently
✅ Each module testable independently
✅ Swapping module doesn't break system
✅ One person can understand one module completely
✅ Adding features = adding modules (not editing existing)
✅ TDD guard provides instant feedback
✅ ccundo enables safe experimentation

---

## Implementation Timeline

| Week | Module | Owner | Milestone |
|------|--------|-------|-----------|
| 1-2 | Bitcoin Interface | bitcoin-onchain-expert | ZMQ streaming works |
| 3-5 | Transaction Processor | general-purpose | Filters match UTXOracle.py |
| 6-9 | Mempool Analyzer | general-purpose | Price estimate ±2% accurate |
| 10-11 | Data Streamer | general-purpose | WebSocket broadcasts state |
| 12-14 | Visualization | general-purpose | Canvas 2D 30fps |
| 15-18 | (Optional) WebGL upgrade | general-purpose | 60fps with 50k points |
| 19+ | (Optional) Rust migration | general-purpose | 10x speedup |

**MVP**: Week 14 (all 5 modules working)
**Production**: Week 18 (WebGL + optimizations)

---

*Modular Architecture v2.0 - MVP KISS Edition*
*Principle: Everything is replaceable*
*Source: Eskil Steenberg + Vibe Coding methodology*
