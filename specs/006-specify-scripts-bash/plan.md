# Implementation Plan: Real-Time Whale Detection Dashboard

**Branch**: `006-specify-scripts-bash` | **Date**: 2025-11-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-specify-scripts-bash/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a real-time whale detection dashboard to visualize Bitcoin whale transactions (>100 BTC) with live WebSocket updates. The dashboard will display whale net flow metrics, urgency scoring, and transaction feeds, connecting to existing backend APIs at `/api/whale/*` endpoints to provide traders with immediate visibility of significant Bitcoin movements.

## Technical Context

**Language/Version**: Python 3.11 (backend), JavaScript ES6+ (frontend)
**Primary Dependencies**: Vanilla JS, Plotly.js, WebSocket API (minimal deps per Constitution I)
**Storage**: DuckDB (existing), browser localStorage for UI preferences
**Testing**: pytest (backend integration tests), manual browser testing (MVP)
**Target Platform**: Modern browsers (Chrome 90+, Firefox 88+, Safari 14+)
**Project Type**: web - Single-page dashboard application
**Performance Goals**: <3s dashboard load, <5s real-time updates, 60 FPS rendering
**Constraints**: <50ms WebSocket latency, <100MB browser memory, reconnection resilience
**Scale/Scope**: 100 concurrent users, 50 transactions in feed, 24h data retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Code Quality & Simplicity
- ✅ **PASS**: Vanilla JS + Canvas 2D (no frameworks)
- ✅ **PASS**: Reuses existing backend APIs
- ✅ **PASS**: Single-purpose dashboard module
- ✅ **PASS**: Minimal dependencies (only Plotly.js for charts)

### Principle II: Test-First Discipline
- ⚠️ **WARN**: Frontend testing strategy needs definition
- ✅ **PASS**: Backend API already tested
- 📋 **ACTION**: Define browser testing approach in research phase

### Principle III: User Experience Consistency
- ✅ **PASS**: Follows existing UTXOracle HTML output patterns
- ✅ **PASS**: Auto-open browser capability planned
- ✅ **PASS**: JSON message format with WebSocket

### Principle IV: Performance Standards
- ✅ **PASS**: Performance targets defined (<3s load, <5s updates)
- ✅ **PASS**: 60 FPS rendering target for Canvas 2D
- ✅ **PASS**: WebSocket latency <50ms requirement

### Principle V: Data Privacy & Security
- ⚠️ **CRITICAL**: Must add authentication for WebSocket connections
- ⚠️ **CRITICAL**: Must implement rate limiting
- ✅ **PASS**: Local-first processing (uses self-hosted backend)
- 📋 **ACTION**: Define auth token strategy in research phase

**GATE RESULT**: CONDITIONAL PASS - Must address security requirements in Phase 0

## Project Structure

### Documentation (this feature)

```
specs/006-specify-scripts-bash/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (in progress)
├── research.md          # Phase 0 output (pending)
├── data-model.md        # Phase 1 output (pending)
├── quickstart.md        # Phase 1 output (pending)
├── contracts/           # Phase 1 output (pending)
│   └── websocket.md     # WebSocket message schemas
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```
frontend/
├── whale_dashboard.html       # Main dashboard page
├── css/
│   └── whale_dashboard.css   # Dashboard styles
├── js/
│   ├── whale_client.js       # WebSocket client
│   ├── whale_charts.js       # Plotly.js chart handlers
│   ├── whale_feed.js         # Transaction feed table
│   └── whale_alerts.js       # Alert notification system
└── assets/
    └── icons/                 # Alert/status icons

api/
├── whale_auth.py              # Authentication middleware
└── whale_security.py          # Rate limiting module

tests/
├── integration/
│   ├── test_whale_websocket.py
│   └── test_whale_auth.py
└── fixtures/
    └── whale_test_data.json
```

**Structure Decision**: Web application structure selected due to frontend+backend nature. Frontend uses vanilla JS with modular files for maintainability. Backend extends existing API with security modules only.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Plotly.js dependency | Interactive charts required | Canvas 2D alone insufficient for complex time series with zoom/pan |
| WebSocket auth tokens | Security for financial data (Principle V) | Open WebSocket would expose sensitive whale signals |

---

## Phase 0: Research & Clarifications

### Items Needing Clarification

1. **WebSocket Authentication Strategy**
   - Token-based vs session-based auth
   - Token refresh mechanism
   - Connection lifecycle management

2. **Rate Limiting Parameters**
   - Requests per minute per user
   - WebSocket message throttling
   - Burst handling strategy

3. **Browser Testing Approach**
   - Manual test checklist vs automated
   - Cross-browser testing scope
   - Performance testing methodology

4. **Chart Library Decision**
   - Plotly.js vs Chart.js vs pure Canvas 2D
   - Bundle size considerations
   - Interactivity requirements

5. **Alert Notification Method**
   - Browser Notification API vs in-page alerts
   - Permission handling
   - Alert persistence strategy

### Research Tasks

- Best practices for WebSocket authentication in financial apps
- Lightweight charting libraries comparison
- Browser notification patterns for trading platforms
- Real-time data visualization performance optimization

---

## Phase 1: Design Outputs (Pending)

**Prerequisites**: Complete Phase 0 research

- `data-model.md`: WebSocket message schemas, auth token structure
- `contracts/websocket.md`: Message format specifications
- `quickstart.md`: Developer setup guide for dashboard
- Agent context update for frontend development

---

## Phase 2: Task Generation (Not part of /plan)

Will be generated by `/speckit.tasks` command after Phase 1 completion.

---

**Next Steps**:
1. Execute Phase 0 research to resolve clarifications
2. Generate research.md with decisions
3. Proceed to Phase 1 design artifacts
4. Re-evaluate Constitution Check post-design