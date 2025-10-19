# UTXOracle Live - Feature Specification (WHAT & WHY)

**Purpose**: Real-time Bitcoin price oracle from mempool data (exchange-free)

---

## Problem Statement

### Current Limitation
UTXOracle.py calculates Bitcoin price from **confirmed blocks only** (historical data). This creates:
- **Latency**: Minimum 10-60 minutes delay (block confirmation time)
- **No real-time signal**: Cannot track live market movements
- **Limited use cases**: Only useful for historical analysis, not live trading/monitoring

### Opportunity
Bitcoin Core broadcasts **mempool transactions** in real-time via ZMQ. We can apply UTXOracle's algorithm to **unconfirmed transactions** to estimate price **live** (updated every 0.5-5 seconds).

### Value Proposition
- **Real-time price updates**: Live BTC/USD estimate from mempool activity
- **Exchange-free**: Trust the blockchain, not custodians (same as UTXOracle.py)
- **Transparency**: Every estimate reproducible from public mempool data
- **New use cases**: Live price monitoring, trading signals, market sentiment

---

## User Scenarios (Prioritized)

### User Story 1 - Real-time Price Monitoring (Priority: P1)

**As a** Bitcoin enthusiast
**I want to** see live BTC/USD price estimates from mempool
**So that** I can track market movements without relying on exchange APIs

**Why this priority**: Core value proposition - without this, there's no product

**Independent Test**: Open browser → see live price updating every 0.5-5 seconds → price matches exchange rates ±2%

**Acceptance Scenarios**:
1. **Given** Bitcoin Core node running with mempool activity
   **When** I open http://localhost:8000
   **Then** I see current price estimate displayed prominently (e.g., "$113,600")

2. **Given** I'm viewing the live dashboard
   **When** new transactions enter mempool
   **Then** price updates within 5 seconds

3. **Given** I leave browser tab open for 1 hour
   **When** I check the price
   **Then** it's still updating (no crashes/freezes)

---

### User Story 2 - Visual Transaction Flow (Priority: P2)

**As a** data analyst
**I want to** visualize mempool transactions as scatter plot (timestamp vs price)
**So that** I can identify price clusters and market trends

**Why this priority**: Enhances understanding beyond raw numbers, aligns with UTXOracle's HTML visualization tradition

**Independent Test**: See live scatter plot with transaction dots appearing in real-time, mouseover shows details

**Acceptance Scenarios**:
1. **Given** I'm viewing the live dashboard
   **When** transactions are processed
   **Then** I see dots appearing on scatter plot (X=timestamp, Y=estimated price)

2. **Given** scatter plot has 500+ transactions
   **When** I hover over a dot
   **Then** tooltip shows: price ($113,550), timestamp (HH:MM:SS)

3. **Given** I'm on laptop with 2000 active transactions
   **When** I watch the visualization
   **Then** it renders smoothly at ≥30 FPS (no lag)

---

### User Story 3 - Confidence Awareness (Priority: P2)

**As a** technical user
**I want to** see confidence score for current price estimate
**So that** I know how reliable the signal is

**Why this priority**: Critical for trust - users need to know when estimate is reliable vs uncertain

**Independent Test**: Price displays with confidence score 0.0-1.0, low confidence shows warning

**Acceptance Scenarios**:
1. **Given** mempool has 1000+ qualifying transactions
   **When** I view dashboard
   **Then** confidence score shows 0.8-1.0 (high confidence)

2. **Given** mempool just started (only 10 transactions)
   **When** I view dashboard
   **Then** confidence score shows 0.1-0.3 + warning "Low confidence - warming up"

3. **Given** I'm watching for 10 minutes
   **When** confidence drops below 0.5
   **Then** price display changes color (yellow/orange) to indicate uncertainty

---

### User Story 4 - System Health Visibility (Priority: P3)

**As a** system operator
**I want to** see mempool processing statistics
**So that** I can verify system is working correctly

**Why this priority**: Important for debugging/monitoring, but not core user value

**Independent Test**: Dashboard shows: total received, filtered, active transactions, uptime

**Acceptance Scenarios**:
1. **Given** system running for 1 hour
   **When** I view dashboard
   **Then** I see stats: "Received: 12,543 | Filtered: 8,234 | Active: 4,309 | Uptime: 1h 02m"

2. **Given** Bitcoin node goes offline
   **When** I check dashboard
   **Then** connection status shows "Disconnected" (red indicator)

3. **Given** I want to validate processing
   **When** I compare "total received" to Bitcoin Core mempool count
   **Then** numbers match ±5% (proves ZMQ working correctly)

---

## Non-Functional Requirements

### Performance
- **Latency**: Price updates within 5 seconds of new transactions entering mempool
- **Throughput**: Handle 1000+ transactions/second (Bitcoin peak load)
- **Uptime**: Run continuously for 7+ days without restart
- **Accuracy**: Price estimate within ±2% of exchange rates (same as UTXOracle.py)

### Scalability
- **Clients**: Support 100 concurrent WebSocket connections (future public API)
- **History**: Maintain 3-hour rolling window (same as UTXOracle.py)
- **Memory**: Backend <500MB RAM, Frontend <50MB browser heap

### Usability
- **Zero setup**: Open browser → works immediately (if Bitcoin node running)
- **No install**: No npm/webpack required for frontend
- **Cross-browser**: Works on Chrome, Firefox, Safari (Canvas API standard)

---

## Success Criteria

### MVP Complete (Target: Week 14)
✅ Real-time price updates every 0.5-5 seconds
✅ Price estimate within ±2% of exchange rates
✅ Live scatter plot visualization (Canvas 2D)
✅ Confidence score displayed accurately
✅ System runs 24+ hours without restart
✅ Works on 3 major browsers (Chrome, Firefox, Safari)

### Production Ready (Target: Week 18, Optional)
✅ Handles 100 concurrent users
✅ Performance: 60 FPS rendering with 50k points (WebGL upgrade)
✅ Historical mempool replay (testing tool)
✅ Monitoring/logging for diagnostics

---

## Out of Scope (MVP)

❌ **Authentication/Authorization**: Public/open system for MVP
❌ **Multi-currency support**: BTC/USD only
❌ **Historical data storage**: In-memory only (no database)
❌ **Mobile app**: Browser-only for MVP
❌ **Exchange comparison**: No external API calls (privacy-first principle)
❌ **Alerts/notifications**: View-only for MVP

---

## Constraints

### Technical
- **Pure Python backend**: No Rust optimization for MVP (future Phase 3)
- **Zero frontend dependencies**: Vanilla JS + Canvas 2D (no React/Vue/build step)
- **Bitcoin Core dependency**: Requires local node with ZMQ enabled
- **Single-server deployment**: No Redis/PostgreSQL for MVP (in-memory state)

### Business
- **Open source**: Blue Oak Model License 1.0.0 (permissive)
- **No external dependencies**: Cannot rely on exchange APIs (privacy-first)
- **Educational transparency**: Code must be understandable by junior developers

### Design
- **KISS principle**: Boring tech, minimal dependencies (UV, FastAPI, PyZMQ only)
- **YAGNI principle**: Don't build features until needed (no premature optimization)
- **Black box architecture**: Each module independently replaceable

---

## Risks & Mitigations

### Risk 1: Mempool price differs significantly from exchange price
**Likelihood**: Medium
**Impact**: High (breaks core value proposition)
**Mitigation**: Historical validation tests comparing mempool estimates vs confirmed block prices

### Risk 2: Bitcoin node ZMQ feed interruption
**Likelihood**: Medium
**Impact**: Medium (system stops working)
**Mitigation**: Auto-reconnect logic (<5 seconds downtime), connection status indicator

### Risk 3: Browser performance degradation with many transactions
**Likelihood**: High (>2000 points)
**Impact**: Medium (laggy UI)
**Mitigation**: Canvas 2D for MVP (<2k points), WebGL upgrade path for production (50k+ points)

### Risk 4: Complexity creep (adding too many features)
**Likelihood**: High (developer enthusiasm)
**Impact**: Medium (delays MVP)
**Mitigation**: Strict adherence to YAGNI - only P1/P2 user stories for MVP

---

## Visual Reference

### Dual-Panel Design (Production Target)

**LEFT Panel** - Confirmed On-Chain Data:
- **Reference**: `examples/UTXOracle_Local_Node_Price.png`
- **Color scheme**: Black background, **cyan/teal points**, green price label
- **Data source**: Confirmed blocks (3-hour window)
- **Update rate**: Every ~10 minutes (new block)
- **Point density**: Very high (thousands of points)
- **Purpose**: Show immutable consensus price from blockchain
- **MVP Status**: ⚠️ Optional for MVP (can be static placeholder or omitted)

**RIGHT Panel** - Mempool Live Data:
- **Reference**: `examples/Screenshot from 2025-10-18 09-26-*.png` (sequential)
- **Color scheme**: Black background, **orange points**, orange/yellow price label
- **Data source**: Real-time mempool transactions
- **Update rate**: Every 0.5-5 seconds (live streaming)
- **Point density**: Medium (300-500 visible points in rolling window)
- **Purpose**: Show real-time market activity before confirmation
- **MVP Status**: ✅ **REQUIRED for MVP** - this is the core feature

### Visual Characteristics (from screenshots)

- **Real-time animation**: Points accumulate right-to-left over time
- **Price display**: Large "Avg: $XXX,XXX" prominently shown (orange for mempool)
- **Metadata**: "Last Block: Xmin", timestamp display
- **Point density**: 300-500 visible points (3-hour rolling window)
- **Layout**: Dual-panel split (~50/50) with synchronized Y-axes

**Key files**:
- `examples/UTXOracle_Local_Node_Price.png` - **LEFT panel reference** (confirmed data, cyan points)
- `examples/Screenshot from 2025-10-18 09-26-57.png` - **RIGHT panel** t=0s baseline
- `examples/Screenshot from 2025-10-18 09-27-03.png` - t=6s (points accumulating)
- `examples/Screenshot from 2025-10-18 09-27-11.png` - t=14s (vertical spread)
- `examples/README.md` - **Detailed dual-panel comparison table**

### Historical Output Reference
UTXOracle.py generates Canvas-based HTML visualizations (example: `historical_data/html_files/UTXOracle_2025-10-16.html`):
- 1000x660px canvas rendering
- Black background with cyan/orange theme
- Interactive tooltips
- Save PNG button
- JavaScript data arrays for plotting

**Design goal**: UTXOracle Live should match this proven visual style.

---

## Related Documents

- **Algorithm Reference**: `UTXOracle.py` (Steps 1-12)
- **Historical Analysis**: `HISTORICAL_DATA.md` (672 days, 99.85% success rate)
- **Visual Reference**: `examples/README.md` (production UI screenshots + analysis)
- **HTML Output Example**: `historical_data/html_files/UTXOracle_2025-10-16.html`
- **Architecture Blueprint**: See SPECKIT_TECH_PLAN.md (tech stack, modules, black box design)
- **Task Breakdown**: `docs/tasks/01-05_*.md` (per-module implementation specs)

---

*Feature Specification v1.0 - UTXOracle Live*
*Created*: 2025-10-19
*Status*: Ready for `/speckit.specify` ingestion
