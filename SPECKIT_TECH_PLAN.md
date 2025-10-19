# UTXOracle Live - Technical Implementation Plan (HOW & TECH)

**Input**: Feature spec from SPECKIT_FEATURE_SPEC.md
**Purpose**: Technical architecture, tech stack, implementation roadmap

---

## Tech Stack (KISS Principle)

### Backend

**Language**: Python 3.11+ (proven, no Rust for MVP)

**Dependency Management**: UV (not pip)
- 10-100x faster than pip
- Deterministic lockfiles (uv.lock)
- Zero-install deployments
- Built-in Python version management

**Core Dependencies** (3 packages only):
```toml
[dependencies]
fastapi = ">=0.104.1"          # WebSocket server
uvicorn[standard] = ">=0.24.0" # ASGI server
pyzmq = ">=25.1.1"             # Bitcoin ZMQ interface
```

**Dev Dependencies**:
```toml
[dev-dependencies]
pytest = ">=7.4.0"
pytest-asyncio = ">=0.21.0"
pytest-watch = ">=4.2.0"       # TDD guard
pytest-testmon = ">=2.1.0"     # Run only affected tests
pytest-cov = ">=4.1.0"         # Coverage reporting
ruff = ">=0.1.6"               # Linting + formatting
```

**Why so few dependencies?**
- Reuse UTXOracle.py parsing functions (pure Python)
- No NumPy/Pandas (overkill for histogram operations)
- No database (in-memory state sufficient for MVP)

---

### Frontend

**Language**: Vanilla JavaScript (ES6+)

**Dependencies**: ZERO
```html
<!-- Canvas 2D API built into browsers -->
<canvas id="mempool-chart"></canvas>
<script src="mempool-viz.js"></script>
```

**Why no build step?**
- Faster development (edit → reload, no webpack/vite)
- Works offline
- Easy to understand/modify
- Zero npm complexity

**Production Upgrade Path** (Phase 2, optional):
```html
<!-- Three.js from CDN (no npm install) -->
<script type="importmap">
{
    "imports": {
        "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"
    }
}
</script>
```

---

### Infrastructure

**Minimal Setup** (no external services):
```
Bitcoin Core (>= v25.0)
  ↓ ZMQ (tcp://127.0.0.1:28332)
  ↓
Python Backend (FastAPI)
  ↓ WebSocket (ws://localhost:8000/ws/mempool)
  ↓
Browser (Canvas 2D)
```

**No Redis, PostgreSQL, Docker required for MVP.**

---

## Architecture (Black Box Modules)

### Core Principle (Eskil Steenberg / Vibe Coding)

1. **One module, one person** - Each module independently owned/developed
2. **Everything replaceable** - If you don't understand it, rewrite it without breaking others
3. **Black box interfaces** - Modules communicate only through data structures
4. **Constant velocity** - Adding features = adding modules (not editing existing)

### Data Flow Pipeline

```
1. Bitcoin Core ZMQ
   ↓ (raw transaction bytes)
2. Module 1: Bitcoin Interface
   ↓ (RawTransaction dataclass)
3. Module 2: Transaction Processor
   ↓ (ProcessedTransaction dataclass)
4. Module 3: Mempool Analyzer
   ↓ (price, confidence, stats)
5. Module 4: Data Streamer (FastAPI)
   ↓ (JSON over WebSocket)
6. Module 5: Visualization (Browser)
   ↓ (Canvas 2D rendering)
```

**Key**: Each arrow is a black box interface. Modules are independently replaceable.

---

## Module Specifications

### Module 1: Bitcoin Interface

**File**: `live/backend/zmq_listener.py`

**Responsibility**: Subscribe to Bitcoin Core ZMQ, yield raw mempool transactions

**Black Box Contract**:
```python
# Input: Bitcoin Core ZMQ endpoint (config)
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

**Performance Targets**:
- Latency: <100ms from Bitcoin broadcast
- Throughput: 10k tx/sec
- Memory: <50MB
- Auto-reconnect: <5s downtime

**Dependencies**: `pyzmq`

**Testing**:
```bash
uv run pytest tests/test_zmq_listener.py -v
uv run pytest tests/integration/test_zmq_live.py --slow  # 5 min with real node
```

**Replaceable**: Yes (swap ZMQ for file replay, mock data, different node)

---

### Module 2: Transaction Processor

**File**: `live/backend/tx_processor.py`

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

**UTXOracle Filters** (from UTXOracle.py Step 6):
- ≤5 inputs
- Exactly 2 outputs
- Not coinbase
- No OP_RETURN
- No witness >500 bytes
- Amounts in [1e-5, 1e5] BTC range

**Performance Targets**:
- Throughput: >1000 tx/sec
- Memory: <100MB for 50k active tx

**Dependencies**: None (pure Python, reuses UTXOracle.py parsing functions)

**Testing**:
```bash
uv run pytest tests/test_tx_processor.py -v
uv run pytest tests/benchmark_tx_processor.py  # Must achieve >1k tx/sec
```

**Replaceable**: Yes (swap filtering algorithm, parsing logic)

---

### Module 3: Mempool Analyzer

**File**: `live/backend/mempool_analyzer.py`

**Responsibility**: Maintain rolling histogram, estimate real-time price

**Black Box Contract**:
```python
# Input: ProcessedTransaction stream
# Output: (price, confidence_score)
# Side Effects: Maintains in-memory rolling histogram (3-hour window)

class MempoolAnalyzer:
    def add_transaction(self, tx: ProcessedTransaction) -> None:
        """Update rolling histogram with new tx"""
        pass

    def estimate_price(self) -> Tuple[float, float]:
        """
        Returns (price, confidence_score)

        Process (from UTXOracle.py):
            1. Normalize histogram (Step 7)
            2. Slide stencils for rough price (Steps 8-9)
            3. Iterative convergence for exact price (Step 11)
        """
        pass
```

**Algorithm** (UTXOracle.py Steps 5-11):
1. Rolling histogram (3-hour window)
2. Remove round BTC amounts (Step 7)
3. Construct price-finding stencil (Step 8)
4. Estimate rough price (Step 9)
5. Convergence algorithm for exact price (Step 11)

**Performance Targets**:
- Price update latency: <500ms
- Memory: <200MB for 50k active tx
- Accuracy: ±2% vs confirmed blocks (historical validation)

**Dependencies**: None (pure Python algorithm)

**Testing**:
```bash
uv run pytest tests/test_mempool_analyzer.py -v
uv run pytest tests/test_historical_validation.py  # Compare mempool vs confirmed
```

**Replaceable**: Yes (swap histogram logic, stencil algorithm, convergence method)

---

### Module 4: Data Streamer

**File**: `live/backend/api.py`

**Responsibility**: FastAPI server, orchestrate pipeline, stream to browser via WebSocket

**Black Box Contract**:
```python
# Input: Orchestrates Modules 1-3
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

**FastAPI Endpoints**:
```python
GET  /              # Serve frontend HTML
GET  /health        # Health check
WS   /ws/mempool    # WebSocket stream
```

**WebSocket Message Format**:
```json
{
    "price": 113600.50,
    "confidence": 0.87,
    "transactions": [
        {"timestamp": 1678901234.1, "price": 113500},
        {"timestamp": 1678901234.2, "price": 113700}
    ],
    "stats": {
        "total_received": 12543,
        "total_filtered": 8234,
        "active_in_window": 4309,
        "uptime_seconds": 3600
    },
    "timestamp": 1678901234.567
}
```

**Performance Targets**:
- Broadcast interval: 500ms
- Concurrent clients: 100
- Latency: <100ms from analyzer update
- Bandwidth: <1MB/sec per client

**Dependencies**: `fastapi`, `uvicorn`

**Testing**:
```bash
uv run pytest tests/test_api.py -v
uv run pytest tests/load_test_websocket.py  # 100 concurrent clients
```

**Run Development Server**:
```bash
uv run uvicorn live.backend.api:app --reload --host 0.0.0.0 --port 8000
```

**Replaceable**: Yes (swap WebSocket for SSE, gRPC, HTTP polling)

---

### Module 5: Visualization Renderer

**File**: `live/frontend/mempool-viz.js`

**Responsibility**: Render real-time scatter plot in browser (Canvas 2D for MVP)

**Black Box Contract**:
```javascript
// Input: WebSocket JSON stream
// Output: Visual display (Canvas 2D)
// Side Effects: DOM manipulation

class MempoolVisualizer {
    constructor(canvasId) { /* ... */ }

    updateData(data) {
        // Receive WebSocket message
        // Update internal state
    }

    render() {
        // Draw scatter plot
        // Target: 30fps (Canvas 2D MVP)
    }
}
```

**Visual Design Reference** (from `examples/` screenshots):

**Dual-Panel Layout** (Production target):
```
┌───────────────────────────┬───────────────────────────┐
│ LEFT: Confirmed (Cyan)    │ RIGHT: Mempool (Orange)   │
│ ⚠️ Optional for MVP       │ ✅ REQUIRED for MVP       │
└───────────────────────────┴───────────────────────────┘
```

**LEFT Panel** (Confirmed On-Chain) - `UTXOracle_Local_Node_Price.png`:
- **Points**: Cyan/Teal (#00CED1), very dense (thousands)
- **Title**: "UTXOracle Local" (cyan #00FFFF)
- **Price**: "Consensus Price $XXX,XXX" (green #00FF00)
- **Footer**: "Consensus Data: identical and immutable..." (green)
- **Update rate**: Every ~10 minutes (new block)
- **MVP Status**: ⚠️ Can be static placeholder or omitted entirely

**RIGHT Panel** (Mempool Live) - Screenshots 09-26-*.png:
- **Points**: Orange (#FFA500), 2-3px diameter, medium density (300-500)
- **Title**: "Mempool" (orange)
- **Price**: "Avg: $XXX,XXX" (orange/yellow #FFB000)
- **Metadata**: "Last Block: Xmin" (bottom right), timestamp
- **Update rate**: Every 0.5-5 seconds (real-time)
- **Animation**: Points appear right-to-left (newest on right edge)
- **Clustering**: Vertical clustering around average price
- **MVP Status**: ✅ **REQUIRED** - this is the core feature

**Common Elements**:
- **Canvas size**: 1000x660px (or responsive)
- **Background**: Black (#000000)
- **Y-axis**: BTC Price ($) - synchronized ranges between panels

**Features**:
- Scatter plot (timestamp vs price)
- Current price display (large text: "Avg: $XXX,XXX")
- Confidence score indicator
- Mouseover tooltip (price, time)
- Auto-scaling Y-axis (e.g., $108k-119k)
- Rolling window (3-hour, points scroll left)

**Performance Targets**:
- FPS: 30fps with <2000 points (Canvas 2D MVP)
- FPS: 60fps with 50k+ points (WebGL production upgrade)
- Memory: <50MB browser heap
- Point capacity: 300-500 visible simultaneously (from screenshots)

**Dependencies**: None (vanilla JS + Canvas API)

**Visual Reference**:
- **LEFT Panel (Confirmed)**: `examples/UTXOracle_Local_Node_Price.png` (cyan points, UTXOracle.py output)
- **RIGHT Panel (Mempool)**: `examples/Screenshot from 2025-10-18 09-26-*.png` (orange points, live animation)
- **Dual-panel comparison**: `examples/README.md` (detailed table with color palettes, differences, priorities)
- **HTML rendering code**: `historical_data/html_files/UTXOracle_2025-10-16.html` (Canvas API reference)

**Testing**:
```bash
# Manual browser testing (Chrome, Firefox, Safari)
open http://localhost:8000

# Compare visually against screenshots in examples/
```

**Replaceable**: Yes (swap Canvas for WebGL, SVG, custom renderer)

---

## Shared Data Models

**File**: `live/shared/models.py` (ONLY file shared between modules)

```python
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

**No cross-module dependencies**. Only data structures shared.

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
    ├── integration/
    │   └── test_zmq_live.py
    ├── benchmark/
    │   └── benchmark_tx_processor.py
    └── fixtures/
        └── sample_tx.bin
```

---

## Development Tools & Workflow

### UV Workspace Setup

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repo, create branch
git clone https://github.com/username/UTXOracle.git
cd UTXOracle
git checkout -b feature/mempool-live

# Initialize UV workspace
uv init

# Add dependencies
uv add fastapi uvicorn pyzmq
uv add --dev pytest pytest-asyncio pytest-watch pytest-testmon pytest-cov ruff

# Generate lockfile (commit this!)
uv lock

# Run application
uv run uvicorn live.backend.api:app --reload
```

### TDD Guard (Continuous Testing)

```bash
# Terminal 1: Continuous test runner
uv run ptw -- --testmon --cov=live/backend

# Terminal 2: Edit code
vim live/backend/zmq_listener.py

# Terminal 1: Auto-runs only affected tests
# ✅ PASSED tests/test_zmq_listener.py::test_connect (0.05s)
# Coverage: 92%
```

**Benefits**:
- Instant feedback (<1 second)
- Only runs tests affected by changes (pytest-testmon)
- Maintains developer velocity

### ccundo (Undo System)

**Path**: `/media/sam/1TB/ccundo` (approved tool)

```bash
# Before launching agent for Task 01
ccundo checkpoint "before-task-01-bitcoin-interface"

# Agent implements Module 1
# ...

# Test module
uv run pytest tests/test_zmq_listener.py

# If tests fail:
ccundo rollback "before-task-01-bitcoin-interface"

# If tests pass:
ccundo checkpoint "task-01-completed"
```

---

## Implementation Phases

### Phase 0: Setup (Week 0)

- Install UV, clone repo, create branch
- Configure Bitcoin Core (enable ZMQ)
- Initialize UV workspace

### Phase 1: Bitcoin Interface (Weeks 1-2)

**Agent**: `bitcoin-onchain-expert`
**Task File**: `docs/tasks/01_bitcoin_interface.md`

**Deliverables**:
- `live/backend/zmq_listener.py`
- `live/backend/config.py`
- `live/backend/models.py`
- Unit tests (>90% coverage)
- Integration test (5 min with real Bitcoin node)

**Acceptance Criteria**:
- [ ] ZMQ connection established
- [ ] Raw transactions yielded in real-time
- [ ] Auto-reconnect works (<5s downtime)
- [ ] Tests pass (>90% coverage)

### Phase 2: Transaction Processor (Weeks 3-5)

**Agent**: `transaction-processor`
**Task File**: `docs/tasks/02_transaction_processor.md`

**Deliverables**:
- `live/backend/tx_processor.py`
- `live/backend/bitcoin_parser.py`
- Unit + benchmark tests

**Acceptance Criteria**:
- [ ] Parses legacy + SegWit tx correctly
- [ ] Filters applied accurately
- [ ] Benchmark: >1000 tx/sec

### Phase 3: Mempool Analyzer (Weeks 6-9)

**Agent**: `mempool-analyzer`
**Task File**: `docs/tasks/03_mempool_analyzer.md`

**Deliverables**:
- `live/backend/mempool_analyzer.py`
- `live/backend/histogram.py`
- `live/backend/stencil.py`
- `live/backend/convergence.py`
- Historical validation report

**Acceptance Criteria**:
- [ ] Price estimate within ±2% of confirmed blocks
- [ ] Process 1000 tx additions/sec
- [ ] Memory <200MB for 50k tx

### Phase 4: Data Streamer (Weeks 10-11)

**Agent**: `data-streamer`
**Task File**: `docs/tasks/04_data_streamer.md`

**Deliverables**:
- `live/backend/api.py`
- `live/backend/orchestrator.py`
- Load tests

**Acceptance Criteria**:
- [ ] WebSocket streams at 500ms intervals
- [ ] Handles 100 concurrent clients

### Phase 5: Visualization (Weeks 12-14)

**Agent**: `visualization-renderer`
**Task File**: `docs/tasks/05_visualization_renderer.md`

**Deliverables**:
- `live/frontend/index.html`
- `live/frontend/mempool-viz.js` (Canvas 2D)
- `live/frontend/styles.css`

**Acceptance Criteria**:
- [ ] 30fps with <2000 points
- [ ] Works on Chrome, Firefox, Safari

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| ZMQ Latency | <100ms | Time from Bitcoin broadcast to yield |
| Tx Processing | >1k tx/sec | Benchmark test |
| Price Update | <500ms | Analyzer latency |
| WebSocket Latency | <100ms | Orchestrator to client |
| Frontend FPS | >30fps | Canvas 2D rendering |
| Memory (Backend) | <300MB | RSS during 50k active tx |
| Memory (Frontend) | <50MB | Browser heap |
| Concurrent Clients | 100 | Load test |
| Uptime (7 days) | >99% | Production monitoring |

---

## Deployment (MVP)

### Development

```bash
# Run backend
uv run uvicorn live.backend.api:app --reload --host 0.0.0.0 --port 8000

# Open browser
open http://localhost:8000
```

### Production (Single Server)

```bash
# Run with production settings
uv run uvicorn live.backend.api:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info \
    --access-log

# (Optional) Nginx reverse proxy for SSL
```

**Note**: Single worker only (in-memory state). No horizontal scaling for MVP.

---

## Rust Migration Path (Future, Optional)

**Phase**: Post-MVP (weeks 19+)

**Motivation**: 10-100x speedup for core algorithm (histogram, stencil, convergence)

**Approach**: Replace Python modules with Rust, keep interfaces identical

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

**Key**: Black box interface allows seamless swap. Other modules don't know/care if histogram is Python or Rust.

---

## Related Technical Documents

- **Module Details**: `docs/tasks/01-05_*.md` (per-module task specifications)
- **Algorithm Reference**: `UTXOracle.py` (Steps 1-12, single-file reference implementation)
- **Visual Design Reference**: `examples/README.md` (dual-panel comparison, color palettes, animation specs)
  - **LEFT Panel**: `examples/UTXOracle_Local_Node_Price.png` (confirmed data, cyan points)
  - **RIGHT Panel**: `examples/Screenshot from 2025-10-18 09-26-*.png` (mempool live, orange points)
- **HTML Output Example**: `historical_data/html_files/UTXOracle_2025-10-16.html` (Canvas rendering code)
- **Advanced Features**: `TECHNICAL_SPEC_ADVANCED.md` (WebGL, Rust, multi-node)
- **Constitution**: `.specify/memory/constitution.md` (code quality, testing, UX, performance principles)

---

*Technical Implementation Plan v1.0 - UTXOracle Live*
*Created*: 2025-10-19
*Status*: Ready for `/speckit.plan` ingestion
