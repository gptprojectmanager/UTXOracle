# UTXOracle Live - Technical Specification (MVP KISS)

**Version**: 1.0 MVP
**Status**: Planning → Implementation
**Timeline**: 10-14 weeks to production-ready system

---

## MVP Goals

1. **Real-time mempool price estimation** using UTXOracle algorithm
2. **WebSocket streaming** to browser clients
3. **Interactive visualization** (Canvas 2D scatter plot)
4. **Zero external dependencies** for frontend
5. **Minimal Python dependencies** for backend (<5 packages)

**Non-Goals (MVP)**:
- WebGL rendering (Phase 2)
- Redis caching (add if needed)
- Rust optimization (Phase 3)
- Multi-node deployment

---

## Tech Stack (KISS Principle)

### Backend

**Language**: Python 3.11+

**Dependency Management**: UV (not pip)
```bash
# Why UV?
# - 10-100x faster than pip
# - Deterministic lockfiles (uv.lock)
# - Built-in Python version management
# - Zero-install deployments

curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Core Dependencies** (3 packages):
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
- No NumPy/Pandas (overkill for this use case)
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
- Faster development (edit → reload)
- No Webpack/Vite complexity
- Works offline
- Easy to understand/modify

**Production upgrade** (Phase 2):
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

**Minimal Setup**:
```
Bitcoin Core (>= v25.0)
  ↓ ZMQ (tcp://127.0.0.1:28332)
  ↓
Python Backend (FastAPI)
  ↓ WebSocket (ws://localhost:8000/ws/mempool)
  ↓
Browser (Canvas 2D)
```

**No external services** (Redis, PostgreSQL, etc.) for MVP.

---

## System Architecture

### Data Flow

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

**Task**: `docs/tasks/01_bitcoin_interface.md`

**Responsibility**: Subscribe to Bitcoin Core ZMQ, yield raw transactions

**Input**: Bitcoin Core ZMQ endpoint (config)

**Output**: `AsyncGenerator[RawTransaction]`

**Performance**:
- Latency: <100ms from Bitcoin broadcast
- Throughput: 10k tx/sec
- Memory: <50MB

**Dependencies**: `pyzmq`

**Testing**:
```bash
uv run pytest tests/test_zmq_listener.py -v
```

---

### Module 2: Transaction Processor

**File**: `live/backend/tx_processor.py`

**Task**: `docs/tasks/02_transaction_processor.md`

**Responsibility**: Parse binary tx, apply UTXOracle filters

**Input**: `RawTransaction`

**Output**: `Optional[ProcessedTransaction]` (None if filtered out)

**Filters** (from UTXOracle.py Step 6):
- ≤5 inputs
- Exactly 2 outputs
- Not coinbase
- No OP_RETURN
- No witness >500 bytes
- Amounts in [1e-5, 1e5] BTC

**Performance**:
- Throughput: >1000 tx/sec
- Memory: <100MB for 50k active tx

**Dependencies**: None (pure Python, reuses UTXOracle.py functions)

**Testing**:
```bash
uv run pytest tests/test_tx_processor.py -v
uv run pytest tests/benchmark_tx_processor.py  # >1k tx/sec
```

---

### Module 3: Mempool Analyzer

**File**: `live/backend/mempool_analyzer.py`

**Task**: `docs/tasks/03_mempool_analyzer.md`

**Responsibility**: Maintain rolling histogram, estimate price

**Input**: `ProcessedTransaction` stream

**Output**: `(price: float, confidence: float)`

**Algorithm** (from UTXOracle.py):
1. Rolling histogram (3-hour window)
2. Remove round BTC amounts (Step 7)
3. Slide stencils for rough price (Steps 8-9)
4. Iterative convergence for exact price (Step 11)

**Performance**:
- Price update latency: <500ms
- Memory: <200MB for 50k active tx
- Accuracy: ±2% vs confirmed blocks (historical validation)

**Dependencies**: None (pure Python algorithm)

**Testing**:
```bash
uv run pytest tests/test_mempool_analyzer.py -v
uv run pytest tests/test_historical_validation.py  # Compare mempool vs confirmed
```

---

### Module 4: Data Streamer

**File**: `live/backend/api.py`

**Task**: `docs/tasks/04_data_streamer.md`

**Responsibility**: FastAPI server, WebSocket streaming

**Input**: Orchestrates Modules 1-3

**Output**: WebSocket JSON stream

**Endpoints**:
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

**Performance**:
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

---

### Module 5: Visualization Renderer

**File**: `live/frontend/mempool-viz.js`

**Task**: `docs/tasks/05_visualization_renderer.md`

**Responsibility**: Real-time scatter plot in browser

**Input**: WebSocket JSON stream

**Output**: Canvas 2D rendering (30fps)

**Features**:
- Scatter plot (timestamp vs price)
- Current price display (large text)
- Confidence score indicator
- Mouseover tooltip (price, time)
- Auto-scaling axes

**Performance**:
- FPS: 30fps with <2000 points
- Memory: <50MB browser heap
- Zero dependencies

**Dependencies**: None (vanilla JS + Canvas API)

**Testing**:
```bash
# Manual browser testing (Chrome, Firefox, Safari)
open http://localhost:8000
```

---

## Development Tools

### UV Workspace Setup

```bash
# Create workspace
uv init utxoracle-live
cd utxoracle-live

# Add dependencies
uv add fastapi uvicorn pyzmq
uv add --dev pytest pytest-asyncio pytest-watch pytest-testmon ruff

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

```bash
# Before launching agent
ccundo checkpoint "before-task-01"

# Agent implements module
# ...

# Test module
uv run pytest tests/test_zmq_listener.py

# If tests fail:
ccundo rollback "before-task-01"

# If tests pass:
ccundo checkpoint "task-01-completed"
```

**Benefits**:
- Safe experimentation with AI-generated code
- Easy rollback if module buggy
- Preview changes before committing

---

## Implementation Phases

### Phase 0: Setup (Week 0)

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repo, create branch
git clone https://github.com/username/UTXOracle.git
cd UTXOracle
git checkout -b feature/mempool-live

# Initialize UV workspace
uv init

# Install Bitcoin Core (if not already)
# Enable ZMQ in bitcoin.conf:
#   zmqpubrawtx=tcp://127.0.0.1:28332
#   zmqpubrawblock=tcp://127.0.0.1:28333
```

---

### Phase 1: Bitcoin Interface (Weeks 1-2)

**Agent**: `bitcoin-onchain-expert`

**Task File**: `docs/tasks/01_bitcoin_interface.md`

**Deliverables**:
- `live/backend/zmq_listener.py`
- `live/backend/config.py`
- `live/backend/models.py`
- Unit tests (>90% coverage)
- Integration test (5 min with real Bitcoin node)

**Launch Agent**:
```python
Task(
    subagent_type="bitcoin-onchain-expert",
    description="Bitcoin ZMQ interface",
    prompt="""
    Implement Module 1 (Bitcoin Interface) as specified in docs/tasks/01_bitcoin_interface.md.

    Requirements:
    - Subscribe to Bitcoin Core ZMQ (tcp://127.0.0.1:28332)
    - Yield RawTransaction dataclass for each mempool tx
    - Auto-reconnect on connection drop (<5s)
    - Unit tests >90% coverage
    - Integration test with real Bitcoin node

    Black box contract:
    - Input: ZMQ endpoint (config)
    - Output: AsyncGenerator[RawTransaction]
    - No side effects (stateless listener)

    Return:
    - Implementation summary
    - Test results
    - Performance metrics (latency, throughput)
    """
)
```

**Acceptance Criteria**:
- [ ] ZMQ connection established
- [ ] Raw transactions yielded in real-time
- [ ] Auto-reconnect works (<5s downtime)
- [ ] Unit tests pass (>90% coverage)
- [ ] Integration test runs 5 min without errors

---

### Phase 2: Transaction Processor (Weeks 3-5)

**Agent**: `general-purpose`

**Task File**: `docs/tasks/02_transaction_processor.md`

**Deliverables**:
- `live/backend/tx_processor.py`
- `live/backend/bitcoin_parser.py` (extracted from UTXOracle.py)
- `live/backend/mempool_state.py`
- Unit tests + benchmark tests

**Launch Agent**: Similar to Phase 1 (use Task file)

**Acceptance Criteria**:
- [ ] Parses legacy + SegWit tx correctly
- [ ] UTXOracle filters applied accurately
- [ ] RBF handling works
- [ ] Benchmark: >1000 tx/sec
- [ ] Unit tests pass (>90% coverage)

---

### Phase 3: Mempool Analyzer (Weeks 6-9)

**Agent**: `general-purpose`

**Task File**: `docs/tasks/03_mempool_analyzer.md`

**Deliverables**:
- `live/backend/mempool_analyzer.py`
- `live/backend/histogram.py`
- `live/backend/stencil.py`
- `live/backend/convergence.py`
- Historical validation report

**Launch Agent**: Use Task file

**Acceptance Criteria**:
- [ ] Rolling histogram updates in real-time
- [ ] Price estimate within ±2% of confirmed blocks
- [ ] Process 1000 tx additions/sec
- [ ] Memory <200MB for 50k tx
- [ ] Historical validation passes

---

### Phase 4: Data Streamer (Weeks 10-11)

**Agent**: `general-purpose`

**Task File**: `docs/tasks/04_data_streamer.md`

**Deliverables**:
- `live/backend/api.py`
- `live/backend/orchestrator.py`
- Load tests (100 concurrent clients)

**Launch Agent**: Use Task file

**Acceptance Criteria**:
- [ ] WebSocket streams at 500ms intervals
- [ ] Handles 100 concurrent clients
- [ ] Health check endpoint works
- [ ] Load tests pass

---

### Phase 5: Visualization (Weeks 12-14)

**Agent**: `general-purpose`

**Task File**: `docs/tasks/05_visualization_renderer.md`

**Deliverables**:
- `live/frontend/index.html`
- `live/frontend/mempool-viz.js` (Canvas 2D)
- `live/frontend/styles.css`
- Browser compatibility tests

**Launch Agent**: Use Task file

**Acceptance Criteria**:
- [ ] Real-time scatter plot updates
- [ ] 30fps with <2000 points
- [ ] Tooltip shows price/time
- [ ] Works on Chrome, Firefox, Safari

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
# nginx.conf:
#   location /ws/mempool {
#       proxy_pass http://localhost:8000;
#       proxy_http_version 1.1;
#       proxy_set_header Upgrade $http_upgrade;
#       proxy_set_header Connection "upgrade";
#   }
```

**Note**: Single worker only (in-memory state).

---

## Testing Strategy

### Unit Tests

```bash
# Run all tests
uv run pytest

# Run specific module
uv run pytest tests/test_zmq_listener.py -v

# Coverage report
uv run pytest --cov=live/backend --cov-report=html
open htmlcov/index.html
```

### Integration Tests

```bash
# Requires running Bitcoin Core node
uv run pytest tests/integration/ -v
```

### Load Tests

```bash
# 100 concurrent WebSocket clients
uv run python tests/load_test_websocket.py
```

### Historical Validation

```bash
# Compare mempool prices vs confirmed prices
uv run pytest tests/test_historical_validation.py -v
```

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

## Success Criteria

✅ **MVP Complete** (Week 14):
- All 5 modules implemented and tested
- Price estimate within ±2% of confirmed blocks
- WebSocket streaming to browser
- Canvas 2D visualization working
- Documentation complete

✅ **Production Ready** (Week 18):
- (Optional) Three.js WebGL rendering
- (Optional) Docker deployment
- (Optional) Monitoring/logging
- Stress tested (24h continuous operation)

---

## Next Steps

1. **Review this spec** - Ensure alignment with project goals
2. **Review task files** - Each module has detailed task in `docs/tasks/`
3. **Setup UV workspace** - Install dependencies, create branch
4. **Launch first agent** - Task 01 (Bitcoin Interface)
5. **TDD workflow** - Use pytest-watch for continuous testing
6. **ccundo checkpoints** - Safe experimentation
7. **Iterate** - One module at a time, test independently

---

**Advanced Features**: See `TECHNICAL_SPEC_ADVANCED.md` for:
- Three.js WebGL rendering (60fps, 100k points)
- Rust optimization (10-100x speedup)
- Multi-node deployment
- Redis caching
- Historical mempool replay

---

*Technical Specification v1.0 - MVP KISS Edition*
*Last Updated*: 2025-10-18
*Status*: Planning Phase
