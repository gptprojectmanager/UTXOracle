# Task Tool Commands - User Story 2 Implementation

**Esegui questi comandi in NUOVE sessioni Claude Code** (una per volta)

---

## 🔧 Session 1: Backend Transaction History (T067-T068)

**Working Directory**: `/media/sam/1TB/UTXOracle`
**Agent**: `mempool-analyzer`
**Estimated Time**: 1-2 hours

### Comando da eseguire:

```python
Task(
    subagent_type="mempool-analyzer",
    description="Implement transaction history backend (T067-T068)",
    prompt="""
# Task: Implement Transaction History Backend (T067-T068)

## Context
You are implementing User Story 2 - Transaction History Buffer for Canvas visualization.
The tests are already written and currently FAILING (RED phase).
You must follow TDD baby-step workflow to make them GREEN.

## Files to Modify
1. `live/backend/mempool_analyzer.py` - Add transaction history tracking
2. `live/backend/api.py` - Include history in WebSocket messages
3. Tests already exist: `tests/test_mempool_analyzer.py::test_transaction_history_buffer`

## TDD Workflow (CRITICAL - Follow Exactly)

### Step 1: Verify Test Fails (RED)
```bash
uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v
```
Expected error: `AttributeError: 'MempoolAnalyzer' object has no attribute 'get_transaction_history'`

### Step 2a: Add Minimal Stub
Edit `live/backend/mempool_analyzer.py`:

```python
# Add at end of MempoolAnalyzer class (before __all__)
def get_transaction_history(self) -> List[Tuple[float, float]]:
    \"\"\"Transaction history for visualization (T067 - User Story 2)\"\"\"
    pass  # Minimal stub - will fail differently
```

Run test again:
```bash
uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v
```
Expected: Different error (returns None instead of list)

### Step 2b: Return Empty List
```python
def get_transaction_history(self) -> List[Tuple[float, float]]:
    \"\"\"Transaction history for visualization (T067)\"\"\"
    return []  # Minimal return - test will still fail
```

Run test again - Expected: AssertionError "History should have entries after adding transactions"

### Step 2c: Add Attribute in __init__
In `MempoolAnalyzer.__init__`, after `self.start_time = time.time()`, add:

```python
# Transaction history for visualization (T067 - User Story 2)
# Stores (timestamp, price) tuples for Canvas scatter plot
# Limited to 500 points for Canvas performance
self.transaction_history: deque = deque(maxlen=500)
```

Also add import at top:
```python
from collections import deque
```

### Step 2d: Update Method to Return History
```python
def get_transaction_history(self) -> List[Tuple[float, float]]:
    \"\"\"
    Get transaction history for visualization (T067 - User Story 2).

    Returns:
        List of (timestamp, price) tuples for Canvas scatter plot.
        Limited to 500 most recent points for Canvas performance.
        Ordered by timestamp (ascending - oldest first).
    \"\"\"
    return list(self.transaction_history)
```

Run test - Still fails (history is empty - we never populate it)

### Step 2e: Populate History in add_transaction()
In `MempoolAnalyzer.add_transaction()`, after updating histogram, add:

```python
# T067: Add to transaction history for visualization
current_price = self.last_price_estimate  # Use last known price
self.transaction_history.append((tx.timestamp, current_price))
```

Run test - Should PASS (GREEN):
```bash
uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v
```
Expected: ✅ PASSED

### Step 3: Commit
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

## T068: Update WebSocket Message to Include History

### Implementation

Edit `live/backend/api.py`, update `DataStreamer.broadcast()` method:

```python
async def broadcast(self, state: MempoolState):
    \"\"\"Broadcast mempool state to all connected clients\"\"\"
    from live.shared.models import TransactionPoint

    # T068: Get transaction history from analyzer
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
            transactions=transaction_history,  # T068: Include history
            stats=SystemStats(
                total_received=state.total_received,
                total_filtered=state.total_filtered,
                active_in_window=state.active_tx_count,
                uptime_seconds=state.uptime_seconds
            ),
            timestamp=time.time()
        )
    )

    # Broadcast to all clients
    await self._broadcast_to_clients(message)
```

### Inject Analyzer Reference

Edit `live/backend/orchestrator.py` (or wherever DataStreamer is instantiated):

```python
# Pass analyzer reference to streamer
streamer.analyzer = analyzer
```

### Verify Test
```bash
uv run pytest tests/test_api.py::test_websocket_includes_transaction_history -v
```
Expected: ✅ PASSED (transactions list now populated)

### Commit
```bash
git add live/backend/api.py live/backend/orchestrator.py
git commit -m "TDD GREEN: T068 - Include transaction history in WebSocket

- Update DataStreamer.broadcast() to include transactions
- Inject analyzer reference in orchestrator
- Test PASSING: test_websocket_includes_transaction_history

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Validation

Run all related tests:
```bash
uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v
uv run pytest tests/test_api.py::test_websocket_includes_transaction_history -v
```

Both should PASS ✅

## Deliverables

1. Transaction history buffer working (300-500 points)
2. WebSocket messages include transaction list
3. All tests GREEN
4. Code committed with proper TDD messages

## Important Notes

- Follow TDD baby-step workflow EXACTLY (stub → minimal → iterate)
- Run pytest after EACH edit
- Commit when tests pass
- Do NOT implement more than needed to pass current test

If you get stuck, refer to `/media/sam/1TB/UTXOracle/CLAUDE.md` section "TDD Implementation Flow" for baby-step examples.
"""
)
```

---

## 🎨 Session 2: Frontend Canvas Visualization (T069-T074)

**Working Directory**: `/media/sam/1TB/UTXOracle`
**Agent**: `visualization-renderer`
**Estimated Time**: 2-3 hours
**Prerequisites**: T067-T068 complete (backend history working)

### Comando da eseguire:

```python
Task(
    subagent_type="visualization-renderer",
    description="Implement Canvas 2D scatter plot (T069-T074)",
    prompt="""
# Task: Implement Canvas 2D Scatter Plot Visualization (T069-T074)

## Context
You are implementing User Story 2 - Canvas scatter plot to visualize transaction history.
The backend (T067-T068) is complete and provides transaction data via WebSocket.
You must implement the Canvas 2D renderer in vanilla JavaScript.

## Visual Reference
- Examples: `/media/sam/1TB/UTXOracle/examples/` - Screenshots of mempool panel
- HTML reference: `/media/sam/1TB/UTXOracle/historical_data/html_files/UTXOracle_2025-10-16.html`

## Files to Modify
1. `live/frontend/mempool-viz.js` - Add MempoolVisualizer class
2. `live/frontend/index.html` - Already has canvas element (no changes needed)
3. Test: `tests/integration/test_frontend.py::test_scatter_plot_renders_transactions`

## Requirements (from spec.md)
- Canvas size: 1000x660px (already in HTML)
- Background: Black (#000000)
- Points: Orange (#FF8C00), radius 2px
- Axes: X = time (horizontal), Y = price (vertical)
- Performance: ≥30 FPS with 2000 points
- Tooltips: Show price + timestamp on hover

## Implementation

### T069: Create MempoolVisualizer Class

Add to `live/frontend/mempool-viz.js` (before UTXOracleLive class):

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
        this.axisColor = '#444444';
        this.labelColor = '#888888';

        // Tooltip state
        this.hoveredPoint = null;
    }

    updateData(transactions) {
        /**
         * Update transaction data from WebSocket (T069)
         * @param {Array} transactions - [{timestamp, price}, ...]
         */
        this.transactions = transactions;
        this.updatePriceRange();
        this.render();
    }

    updatePriceRange() {
        // T070: Auto-scale Y-axis based on data
        if (this.transactions.length === 0) {
            this.priceRange = {min: 0, max: 200000};
            return;
        }

        const prices = this.transactions.map(t => t.price);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);

        // Add 5% padding
        this.priceRange.min = minPrice * 0.95;
        this.priceRange.max = maxPrice * 1.05;
    }

    render() {
        // T069: Main render loop
        this.clear();
        this.drawAxes();      // T070
        this.drawPoints();    // T071

        if (this.hoveredPoint) {
            this.drawTooltip(this.hoveredPoint);  // T072
        }
    }

    clear() {
        this.ctx.fillStyle = this.backgroundColor;
        this.ctx.fillRect(0, 0, this.width, this.height);
    }

    drawAxes() {
        // T070: Draw X (time) and Y (price) axes with labels
        this.ctx.strokeStyle = this.axisColor;
        this.ctx.lineWidth = 1;

        const leftMargin = 80;
        const bottomMargin = 50;
        const rightMargin = 30;
        const topMargin = 30;

        // Y-axis (left)
        this.ctx.beginPath();
        this.ctx.moveTo(leftMargin, topMargin);
        this.ctx.lineTo(leftMargin, this.height - bottomMargin);
        this.ctx.stroke();

        // X-axis (bottom)
        this.ctx.beginPath();
        this.ctx.moveTo(leftMargin, this.height - bottomMargin);
        this.ctx.lineTo(this.width - rightMargin, this.height - bottomMargin);
        this.ctx.stroke();

        // Price labels (Y-axis)
        this.ctx.fillStyle = this.labelColor;
        this.ctx.font = '12px monospace';
        this.ctx.textAlign = 'right';
        this.ctx.textBaseline = 'middle';

        const priceSteps = 5;
        for (let i = 0; i <= priceSteps; i++) {
            const price = this.priceRange.min +
                (this.priceRange.max - this.priceRange.min) * (i / priceSteps);
            const y = this.height - bottomMargin -
                ((this.height - bottomMargin - topMargin) * i / priceSteps);

            this.ctx.fillText(`$${Math.round(price).toLocaleString()}`, leftMargin - 10, y);
        }

        // Time label (X-axis)
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'top';
        this.ctx.fillText('Time →', this.width / 2, this.height - bottomMargin + 10);

        // Price label (Y-axis)
        this.ctx.save();
        this.ctx.translate(20, this.height / 2);
        this.ctx.rotate(-Math.PI / 2);
        this.ctx.fillText('Price (USD) →', 0, 0);
        this.ctx.restore();
    }

    drawPoints() {
        // T071: Draw transaction points (right-to-left accumulation)
        if (this.transactions.length === 0) return;

        this.ctx.fillStyle = this.pointColor;

        const leftMargin = 80;
        const bottomMargin = 50;
        const rightMargin = 30;
        const topMargin = 30;

        const plotWidth = this.width - leftMargin - rightMargin;
        const plotHeight = this.height - topMargin - bottomMargin;

        const timeRange = this.getTimeRange();
        if (timeRange === 0) return;

        const xScale = plotWidth / timeRange;
        const yScale = plotHeight / (this.priceRange.max - this.priceRange.min);

        const minTimestamp = Math.min(...this.transactions.map(t => t.timestamp));

        for (const tx of this.transactions) {
            // T071: Map timestamp to X (oldest on left, newest on right)
            const x = leftMargin + ((tx.timestamp - minTimestamp) * xScale);

            // Map price to Y (higher price = higher on canvas)
            const y = this.height - bottomMargin -
                ((tx.price - this.priceRange.min) * yScale);

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

            const nearest = this.findNearestPoint(mouseX, mouseY);

            if (nearest && nearest.distance < 10) {
                this.hoveredPoint = {
                    x: mouseX,
                    y: mouseY,
                    transaction: nearest.transaction
                };
                this.canvas.style.cursor = 'pointer';
            } else {
                this.hoveredPoint = null;
                this.canvas.style.cursor = 'default';
            }

            this.render();  // Redraw to show/hide tooltip
        });

        this.canvas.addEventListener('mouseleave', () => {
            this.hoveredPoint = null;
            this.canvas.style.cursor = 'default';
            this.render();
        });
    }

    findNearestPoint(mouseX, mouseY) {
        if (this.transactions.length === 0) return null;

        const leftMargin = 80;
        const bottomMargin = 50;
        const rightMargin = 30;
        const topMargin = 30;

        const plotWidth = this.width - leftMargin - rightMargin;
        const plotHeight = this.height - topMargin - bottomMargin;

        const timeRange = this.getTimeRange();
        if (timeRange === 0) return null;

        const xScale = plotWidth / timeRange;
        const yScale = plotHeight / (this.priceRange.max - this.priceRange.min);

        const minTimestamp = Math.min(...this.transactions.map(t => t.timestamp));

        let nearest = null;
        let minDistance = Infinity;

        for (const tx of this.transactions) {
            const x = leftMargin + ((tx.timestamp - minTimestamp) * xScale);
            const y = this.height - bottomMargin -
                ((tx.price - this.priceRange.min) * yScale);

            const distance = Math.sqrt(
                Math.pow(mouseX - x, 2) + Math.pow(mouseY - y, 2)
            );

            if (distance < minDistance) {
                minDistance = distance;
                nearest = {transaction: tx, distance};
            }
        }

        return nearest;
    }

    drawTooltip(hoverData) {
        // T072: Draw tooltip with price and timestamp
        const tx = hoverData.transaction;
        const date = new Date(tx.timestamp * 1000);
        const timeStr = date.toLocaleTimeString();
        const priceStr = `$${tx.price.toFixed(2)}`;
        const text = `${priceStr} @ ${timeStr}`;

        // Tooltip background
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.9)';
        const padding = 10;
        const textWidth = this.ctx.measureText(text).width;

        let tooltipX = hoverData.x + 15;
        let tooltipY = hoverData.y - 35;

        // Keep tooltip in bounds
        if (tooltipX + textWidth + padding * 2 > this.width) {
            tooltipX = hoverData.x - textWidth - padding * 2 - 15;
        }
        if (tooltipY < 0) {
            tooltipY = hoverData.y + 15;
        }

        this.ctx.fillRect(tooltipX, tooltipY, textWidth + padding * 2, 30);

        // Tooltip text
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.font = '14px monospace';
        this.ctx.textAlign = 'left';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText(text, tooltipX + padding, tooltipY + 15);
    }
}
```

### Integrate with Existing WebSocket Client

Update `UTXOracleLive` class in `mempool-viz.js`:

```javascript
class UTXOracleLive {
    constructor() {
        this.wsClient = new MempoolWebSocketClient();
        this.uiController = new UIController();

        // T069: Initialize visualizer
        this.visualizer = new MempoolVisualizer('mempool-canvas');
        this.visualizer.enableTooltips();  // T072

        // ... existing WebSocket setup code ...
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

## Validation

### Test Suite
```bash
uv run pytest tests/integration/test_frontend.py::test_scatter_plot_renders_transactions -v
```
Expected: ✅ PASSED (MempoolVisualizer class now exists)

### Manual Testing (T074)
```bash
# Terminal 1: Start backend
uv run uvicorn live.backend.api:app --reload

# Terminal 2: Open browser
open http://localhost:8000

# DevTools (F12) → Console:
# Should see: [App] Mempool update: {...}

# Visual checks:
# ✅ Canvas shows scatter plot with orange points
# ✅ Points appear in real-time
# ✅ Hover shows tooltip with price + timestamp
# ✅ Axes labeled correctly (Time, Price)

# Performance check (DevTools → Performance tab):
# Record for 10 seconds, check FPS
# ✅ Should be ≥30 FPS with 2000 points
```

### Screenshots for Documentation
Take screenshots:
- `canvas_initial.png` - Canvas with first points
- `canvas_full.png` - Canvas with 500 points
- `canvas_tooltip.png` - Hovering over point showing tooltip

---

## Commit

```bash
git add live/frontend/mempool-viz.js tests/integration/test_frontend.py
git commit -m "Feature: Canvas scatter plot visualization (T069-T074)

- Implement MempoolVisualizer class with Canvas 2D
- Add auto-scaling axes (X=time, Y=price)
- Real-time point accumulation (orange, 2px radius)
- Hover tooltips with price + timestamp
- Performance: 30+ FPS with 2000 points

Tests PASSING:
- test_scatter_plot_renders_transactions ✅

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Deliverables

1. MempoolVisualizer class implemented
2. Canvas renders scatter plot (1000x660px, black bg, orange points)
3. Axes with labels and auto-scaling
4. Real-time updates from WebSocket
5. Hover tooltips working
6. Performance validated (≥30 FPS)
7. Test PASSING
8. Screenshots captured

## Important Notes

- Use vanilla JavaScript (no frameworks)
- Canvas 2D API only (no WebGL for MVP)
- Performance target: ≥30 FPS with 2000 points
- Visual style matches spec.md (black bg, orange theme)
- Tooltips should not block points

If you need visual reference, see:
- `/media/sam/1TB/UTXOracle/examples/` for screenshots
- `/media/sam/1TB/UTXOracle/historical_data/html_files/UTXOracle_2025-10-16.html` for Canvas example
"""
)
```

---

## 📋 Execution Checklist

### Before Starting
- [ ] Ensure working directory is `/media/sam/1TB/UTXOracle`
- [ ] Ensure backend tests are passing (T001-T061)
- [ ] Ensure delegation files exist (`DELEGATION_T067-T074.md`)

### Session 1 (Backend)
- [ ] Open new Claude Code session
- [ ] Copy/paste Session 1 command above
- [ ] Wait for completion (~1-2 hours)
- [ ] Verify tests pass: `uv run pytest tests/test_mempool_analyzer.py::test_transaction_history_buffer -v`

### Session 2 (Frontend)
- [ ] Open new Claude Code session (can run in parallel with Session 1)
- [ ] Copy/paste Session 2 command above
- [ ] Wait for completion (~2-3 hours)
- [ ] Verify test passes: `uv run pytest tests/integration/test_frontend.py::test_scatter_plot_renders_transactions -v`
- [ ] Manual browser validation

### After Both Complete
- [ ] Run full test suite: `uv run pytest tests/ -v`
- [ ] Update `tasks.md` to mark T067-T074 as complete
- [ ] Commit delegation completion
- [ ] Proceed to User Story 3 or manual validation (T062-T064)

---

**Note**: These commands are self-contained. Copy-paste directly into new Claude Code sessions.
