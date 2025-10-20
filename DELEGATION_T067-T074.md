# Delegation Package: User Story 2 Implementation (T067-T074)

**Feature**: Canvas Scatter Plot Visualization + Transaction History Backend
**Status**: Tests written (RED phase), implementation pending
**Agent**: `mempool-analyzer` (backend) + `visualization-renderer` (frontend)
**Estimated Time**: 3-4 hours total

---

## 📋 Context

**What's Done** (T001-T066):
- ✅ Backend pipeline working (ZMQ → TX Processor → Analyzer → WebSocket)
- ✅ Frontend scaffold exists (HTML + CSS + basic WebSocket client)
- ✅ Tests written for T065-T066 (currently FAILING - RED phase)

**What Needs Implementation** (T067-T074):
- Backend: Transaction history buffer (300-500 points)
- Backend: Include history in WebSocket messages
- Frontend: Canvas 2D scatter plot renderer
- Frontend: Axes, tooltips, real-time updates

**Visual Reference**:
- `/media/sam/1TB/UTXOracle/examples/` - Screenshots showing mempool panel
- `/media/sam/1TB/UTXOracle/historical_data/html_files/UTXOracle_2025-10-16.html` - Canvas rendering example

---

## 🎯 Task Breakdown

### **Part 1: Backend Transaction History** (T067-T068)

**Agent**: `mempool-analyzer` or `general-purpose`
**Files**: `live/backend/mempool_analyzer.py`, `live/backend/api.py`
**Time**: 1-2 hours

#### T067: Transaction History Buffer

**Current State**:
- ✅ Test written: `tests/test_mempool_analyzer.py::test_transaction_history_buffer`
- ❌ Test FAILING: `AttributeError: 'MempoolAnalyzer' object has no attribute 'get_transaction_history'`

**TDD Baby Steps** (CRITICAL - Follow EXACTLY):

```bash
# Step 1: Verify test fails
uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v
# Expected: AttributeError: 'MempoolAnalyzer' object has no attribute 'get_transaction_history'
```

**Step 2a**: Add MINIMAL stub method to `mempool_analyzer.py`

```python
# Add at end of MempoolAnalyzer class (before __all__)
def get_transaction_history(self) -> List[Tuple[float, float]]:
    """Transaction history for visualization (T067)"""
    pass  # Minimal stub
```

```bash
# Run test again
uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v
# Expected: Different error (returns None instead of list)
```

**Step 2b**: Return empty list

```python
def get_transaction_history(self) -> List[Tuple[float, float]]:
    """Transaction history for visualization (T067)"""
    return []  # Minimal return
```

```bash
# Run test again
uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v
# Expected: AssertionError: "History should have entries after adding transactions"
```

**Step 2c**: Add attribute initialization in `__init__`

```python
# In MempoolAnalyzer.__init__, after self.start_time:
self.transaction_history: deque = deque(maxlen=500)  # T067 - User Story 2
```

**Step 2d**: Update method to return history

```python
def get_transaction_history(self) -> List[Tuple[float, float]]:
    """Transaction history for visualization (T067)"""
    return list(self.transaction_history)  # Convert deque to list
```

```bash
# Run test again
uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v
# Expected: Still fails - history is empty (we never populate it)
```

**Step 2e**: Populate history in `add_transaction()` method

```python
# In add_transaction(), after updating histogram:
def add_transaction(self, tx: ProcessedTransaction) -> None:
    """Add transaction to histogram (Step 6)"""
    # ... existing histogram code ...

    # T067: Add to transaction history for visualization
    current_price = self.last_price_estimate  # Use last known price
    self.transaction_history.append((tx.timestamp, current_price))
```

```bash
# Run test - should PASS (GREEN)
uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v
# Expected: ✅ PASSED
```

**Commit**:
```bash
git add live/backend/mempool_analyzer.py tests/test_mempool_analyzer.py
git commit -m "TDD GREEN: T067 - Transaction history buffer (300-500 points)

- Add transaction_history deque (maxlen=500)
- Implement get_transaction_history() method
- Populate history in add_transaction()
- Test PASSING: test_transaction_history_buffer

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

#### T068: Update WebSocket Message

**Current State**:
- ✅ Test exists: `tests/test_api.py::test_websocket_includes_transaction_history`
- ❌ Currently PASSING with empty transactions list (needs update)

**Implementation**:

1. Update `DataStreamer.broadcast()` in `live/backend/api.py`:

```python
# In DataStreamer.broadcast(state: MempoolState)
async def broadcast(self, state: MempoolState):
    """Broadcast mempool state to all connected clients"""
    # Get transaction history from analyzer (T068)
    transaction_history = []
    if hasattr(self, 'analyzer') and self.analyzer:
        history = self.analyzer.get_transaction_history()
        transaction_history = [
            TransactionPoint(timestamp=ts, price=price)
            for ts, price in history
        ]

    # Create message with transactions
    message = WebSocketMessage(
        data=MempoolUpdateData(
            price=state.price,
            confidence=state.confidence,
            transactions=transaction_history,  # Include history
            stats=SystemStats(...),
            timestamp=time.time()
        )
    )

    # Broadcast to clients
    await self._broadcast_to_clients(message)
```

2. Inject analyzer reference in orchestrator:

```python
# In orchestrator.py, pass analyzer to DataStreamer
streamer.analyzer = analyzer
```

**Test**:
```bash
uv run pytest tests/test_api.py::test_websocket_includes_transaction_history -v
# Expected: ✅ PASSED (transactions list now populated)
```

---

### **Part 2: Frontend Canvas Visualization** (T069-T074)

**Agent**: `visualization-renderer` or `ccbrowser`/`ccfullbrowser`
**Files**: `live/frontend/mempool-viz.js`
**Time**: 2-3 hours

#### Prerequisites

Check frontend structure test passes:
```bash
uv run pytest tests/integration/test_frontend.py::test_scatter_plot_renders_transactions -v
# Currently FAILING: "MempoolVisualizer class/function not found"
```

#### Implementation Steps

**T069: Canvas 2D Scatter Plot Class**

Add to `live/frontend/mempool-viz.js`:

```javascript
class MempoolVisualizer {
    constructor(canvasId = 'mempool-canvas') {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            throw new Error(`Canvas element #${canvasId} not found`);
        }

        this.ctx = this.canvas.getContext('2d');
        this.width = this.canvas.width;   // 1000px
        this.height = this.canvas.height; // 660px

        // Data
        this.transactions = [];  // Array of {timestamp, price}
        this.priceRange = {min: 0, max: 200000};  // Auto-scaled

        // Visual settings (from spec.md)
        this.pointColor = '#FF8C00';  // Orange
        this.pointRadius = 2;
        this.backgroundColor = '#000000';  // Black
    }

    updateData(transactions) {
        /**
         * Update transaction data from WebSocket
         * @param {Array} transactions - [{timestamp, price}, ...]
         */
        this.transactions = transactions;
        this.updatePriceRange();
        this.render();
    }

    updatePriceRange() {
        // Auto-scale Y-axis based on data (T070)
        if (this.transactions.length === 0) return;

        const prices = this.transactions.map(t => t.price);
        this.priceRange.min = Math.min(...prices) * 0.95;
        this.priceRange.max = Math.max(...prices) * 1.05;
    }

    render() {
        // T069: Clear and draw scatter plot
        this.clear();
        this.drawAxes();      // T070
        this.drawPoints();    // T071
    }

    clear() {
        this.ctx.fillStyle = this.backgroundColor;
        this.ctx.fillRect(0, 0, this.width, this.height);
    }

    drawAxes() {
        // T070: Draw X (time) and Y (price) axes with labels
        this.ctx.strokeStyle = '#444';
        this.ctx.lineWidth = 1;

        // Y-axis (left)
        this.ctx.beginPath();
        this.ctx.moveTo(50, 20);
        this.ctx.lineTo(50, this.height - 40);
        this.ctx.stroke();

        // X-axis (bottom)
        this.ctx.beginPath();
        this.ctx.moveTo(50, this.height - 40);
        this.ctx.lineTo(this.width - 20, this.height - 40);
        this.ctx.stroke();

        // Price labels
        this.ctx.fillStyle = '#888';
        this.ctx.font = '12px monospace';
        this.ctx.textAlign = 'right';

        const priceSteps = 5;
        for (let i = 0; i <= priceSteps; i++) {
            const price = this.priceRange.min +
                (this.priceRange.max - this.priceRange.min) * (i / priceSteps);
            const y = this.height - 40 - ((this.height - 60) * i / priceSteps);

            this.ctx.fillText(`$${price.toFixed(0)}`, 45, y + 4);
        }
    }

    drawPoints() {
        // T071: Draw transaction points (right-to-left accumulation)
        if (this.transactions.length === 0) return;

        this.ctx.fillStyle = this.pointColor;

        const timeRange = this.getTimeRange();
        const xScale = (this.width - 70) / timeRange;
        const yScale = (this.height - 60) / (this.priceRange.max - this.priceRange.min);

        for (const tx of this.transactions) {
            // Map timestamp to X (newest on right)
            const x = 50 + ((tx.timestamp - this.transactions[0].timestamp) * xScale);

            // Map price to Y (higher price = higher on canvas)
            const y = this.height - 40 - ((tx.price - this.priceRange.min) * yScale);

            // Draw point
            this.ctx.beginPath();
            this.ctx.arc(x, y, this.pointRadius, 0, Math.PI * 2);
            this.ctx.fill();
        }
    }

    getTimeRange() {
        if (this.transactions.length < 2) return 1;
        const timestamps = this.transactions.map(t => t.timestamp);
        return Math.max(...timestamps) - Math.min(...timestamps);
    }

    // T072: Hover tooltips
    enableTooltips() {
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            // Find nearest point
            const nearest = this.findNearestPoint(mouseX, mouseY);
            if (nearest && nearest.distance < 10) {
                this.showTooltip(mouseX, mouseY, nearest.transaction);
            } else {
                this.hideTooltip();
            }
        });
    }

    findNearestPoint(mouseX, mouseY) {
        // Implementation for finding closest transaction point
        // Returns {transaction, distance}
    }

    showTooltip(x, y, transaction) {
        // Draw tooltip with price and timestamp
        const text = `$${transaction.price.toFixed(2)} @ ${new Date(transaction.timestamp * 1000).toLocaleTimeString()}`;

        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
        this.ctx.fillRect(x + 10, y - 30, 200, 25);

        this.ctx.fillStyle = '#FFF';
        this.ctx.font = '12px monospace';
        this.ctx.textAlign = 'left';
        this.ctx.fillText(text, x + 15, y - 12);
    }
}
```

**Integration with existing WebSocket client**:

```javascript
// In UTXOracleLive class, add visualizer
class UTXOracleLive {
    constructor() {
        this.wsClient = new MempoolWebSocketClient();
        this.uiController = new UIController();
        this.visualizer = new MempoolVisualizer('mempool-canvas');  // NEW
        this.visualizer.enableTooltips();  // T072

        // ... existing code ...
    }

    handleMempoolUpdate(message) {
        const data = message.data;

        this.uiController.updatePrice(data.price);
        this.uiController.updateConfidence(data.confidence);
        this.uiController.updateStats(data.stats);

        // T069-T071: Update Canvas visualization
        if (data.transactions && data.transactions.length > 0) {
            this.visualizer.updateData(data.transactions);
        }
    }
}
```

---

## ✅ Validation

### Test Suite
```bash
# All tests should PASS
uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v
uv run pytest tests/test_api.py::test_websocket_includes_transaction_history -v
uv run pytest tests/integration/test_frontend.py::test_scatter_plot_renders_transactions -v
```

### Manual Testing (T074)
```bash
# Terminal 1: Start backend
uv run uvicorn live.backend.api:app --reload

# Terminal 2: Open browser
open http://localhost:8000

# Verify:
# ✅ Canvas shows scatter plot with orange points
# ✅ Points appear in real-time (right-to-left)
# ✅ Hover shows tooltip with price + timestamp
# ✅ Rendering ≥30 FPS with 2000 points (check DevTools Performance tab)
```

---

## 📊 Success Criteria

**T067-T068 (Backend)**:
- ✅ `get_transaction_history()` returns list of (timestamp, price) tuples
- ✅ History limited to 500 points
- ✅ WebSocket messages include transactions
- ✅ Tests PASSING

**T069-T074 (Frontend)**:
- ✅ Canvas renders scatter plot (1000x660px, black bg, orange points)
- ✅ X-axis = time, Y-axis = price (auto-scaled)
- ✅ Points accumulate right-to-left
- ✅ Hover tooltips work
- ✅ Performance ≥30 FPS with 2000 points
- ✅ Test `test_scatter_plot_renders_transactions` PASSING

---

## 🚀 Execution

**Recommended Approach**:
1. New Claude Code session with `mempool-analyzer` agent for T067-T068
2. New Claude Code session with `visualization-renderer` agent for T069-T074
3. Final validation in browser with `ccbrowser` MCP

**Alternative**: Single session with `general-purpose` agent, but TDD discipline required!
