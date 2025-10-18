# UTXOracle Live - Advanced Technical Specification

**Version**: 2.0 Production
**Prerequisites**: MVP Complete (TECHNICAL_SPEC.md)
**Timeline**: +4-8 weeks after MVP

---

## Overview

This document outlines production features and optimizations **beyond MVP**:

1. **Three.js WebGL Rendering** - 60fps with 100k points
2. **Rust Core Optimization** - 10-100x speedup
3. **Redis State Caching** - Distributed deployment
4. **Historical Mempool Replay** - Testing/research
5. **Multi-Node Deployment** - Load balancing, HA

**Start Here**: Only after MVP is complete and validated in production.

---

## Feature 1: Three.js WebGL Rendering

### Motivation

**Problem**: Canvas 2D lags with >2000 points
**Solution**: GPU-accelerated rendering with Three.js

### Performance Comparison

| Renderer | Max Points @ 60fps | Memory | Dependencies |
|----------|-------------------|---------|--------------|
| Canvas 2D (MVP) | 2,000 | 30MB | None |
| Three.js WebGL | 100,000 | 80MB | CDN import |

### Implementation

**File**: `live/frontend/mempool-viz-webgl.js`

**Tech Stack**:
```html
<script type="importmap">
{
    "imports": {
        "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"
    }
}
</script>
<script type="module">
import * as THREE from 'three';
import { MempoolVisualizerWebGL } from './mempool-viz-webgl.js';

const viz = new MempoolVisualizerWebGL('chart-container');
</script>
```

**Core Rendering Loop**:
```javascript
// mempool-viz-webgl.js

import * as THREE from 'three';

export class MempoolVisualizerWebGL {
    constructor(containerId) {
        this.container = document.getElementById(containerId);

        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x000000);

        // Orthographic camera (2D plot in 3D space)
        this.camera = new THREE.OrthographicCamera(
            0, 1000,  // left, right
            660, 0,   // top, bottom
            0.1, 1000 // near, far
        );
        this.camera.position.z = 1;

        // WebGL renderer
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(1000, 660);
        this.container.appendChild(this.renderer.domElement);

        // Points geometry
        this.geometry = new THREE.BufferGeometry();
        this.material = new THREE.PointsMaterial({
            size: 2,
            vertexColors: true,  // Per-point colors
            sizeAttenuation: false
        });
        this.points = new THREE.Points(this.geometry, this.material);
        this.scene.add(this.points);

        // Animation loop
        this.animate();
    }

    updateData(transactions) {
        const count = transactions.length;

        // Allocate typed arrays (GPU-friendly)
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);

        transactions.forEach((tx, i) => {
            // Position (x, y, z)
            positions[i * 3] = this.scaleX(tx.timestamp);
            positions[i * 3 + 1] = this.scaleY(tx.price);
            positions[i * 3 + 2] = 0;

            // Color (R, G, B) with age-based fade
            const age = Date.now() / 1000 - tx.timestamp;
            const alpha = Math.max(0, 1 - age / 3600);  // Fade over 1 hour

            colors[i * 3] = 1.0;         // R (orange)
            colors[i * 3 + 1] = 0.4 * alpha;  // G
            colors[i * 3 + 2] = 0.0;     // B
        });

        // Update geometry buffers
        this.geometry.setAttribute('position',
            new THREE.BufferAttribute(positions, 3));
        this.geometry.setAttribute('color',
            new THREE.BufferAttribute(colors, 3));
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.renderer.render(this.scene, this.camera);
    }

    scaleX(timestamp) {
        // Map timestamp to [120, 910] (plot area)
        return 120 + ((timestamp - this.xmin) / (this.xmax - this.xmin)) * 790;
    }

    scaleY(price) {
        // Map price to [100, 560] (inverted Y)
        return 560 - ((price - this.ymin) / (this.ymax - this.ymin)) * 460;
    }
}
```

**Advanced Features**:
1. **Point fade-out** - Older transactions gradually disappear
2. **Smooth zoom/pan** - OrbitControls for interaction
3. **Particle trails** - Visual effect for transaction flow
4. **Heatmap overlay** - Density visualization

### Fallback Strategy

```javascript
// index.html - Progressive enhancement

try {
    const renderer = new THREE.WebGLRenderer();
    // WebGL supported → use Three.js
    import('./mempool-viz-webgl.js').then(m => {
        new m.MempoolVisualizerWebGL('chart');
    });
} catch (e) {
    // WebGL not supported → fallback to Canvas 2D
    import('./mempool-viz.js').then(m => {
        new m.MempoolVisualizer('chart');
    });
}
```

### Performance Benchmarking

```bash
# Create test dataset
uv run python tests/create_webgl_benchmark.py --points 100000

# Serve locally
uv run uvicorn live.backend.api:app

# Open browser, measure FPS
open http://localhost:8000

# Expected: 60fps steady with 100k points
```

**Timeline**: 2-3 weeks

**Priority**: Medium (only if Canvas lags in production)

---

## Feature 2: Rust Core Optimization

### Motivation

**Problem**: Python histogram/stencil/convergence too slow for >10k tx/sec
**Solution**: Rewrite performance-critical modules in Rust, keep Python interface

### Performance Targets

| Module | Python Baseline | Rust Target | Speedup |
|--------|----------------|-------------|---------|
| Histogram | 1k tx/sec | 50k tx/sec | 50x |
| Stencil Matcher | 100 slides/sec | 10k slides/sec | 100x |
| Convergence | 10 iterations/sec | 1k iterations/sec | 100x |

### Architecture

**Keep**:
- Python modules (ZMQ, FastAPI, orchestrator)
- Module interfaces (black box principle)

**Replace**:
- `histogram.py` → `core_rust.Histogram`
- `stencil.py` → `core_rust.StencilMatcher`
- `convergence.py` → `core_rust.PriceConvergence`

### Implementation

**Step 1: Setup Rust Project**

```bash
# Create Rust library
cargo new --lib core_rust
cd core_rust
```

```toml
# core_rust/Cargo.toml

[package]
name = "core_rust"
version = "0.1.0"
edition = "2021"

[lib]
name = "core_rust"
crate-type = ["cdylib"]  # Python extension

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
numpy = "0.20"  # For efficient array passing
```

**Step 2: Implement Histogram in Rust**

```rust
// core_rust/src/histogram.rs

use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct Histogram {
    bins: Vec<f64>,
    counts: Vec<f64>,
    first_bin_value: f64,
    range_bin_values: f64,
}

#[pymethods]
impl Histogram {
    #[new]
    fn new() -> Self {
        let bins = Self::create_bins();
        let count = bins.len();

        Histogram {
            bins,
            counts: vec![0.0; count],
            first_bin_value: -6.0,
            range_bin_values: 12.0,
        }
    }

    fn add_amount(&mut self, amount: f64) {
        if amount < 1e-5 || amount > 1e5 {
            return;
        }

        let bin_idx = self.find_bin(amount);
        if let Some(idx) = bin_idx {
            self.counts[idx] += 1.0;
        }
    }

    fn remove_amount(&mut self, amount: f64) {
        if let Some(idx) = self.find_bin(amount) {
            self.counts[idx] = (self.counts[idx] - 1.0).max(0.0);
        }
    }

    fn normalize(&mut self) {
        let sum: f64 = self.counts[201..1601].iter().sum();

        if sum == 0.0 {
            return;
        }

        for i in 201..1601 {
            self.counts[i] /= sum;
            if self.counts[i] > 0.008 {
                self.counts[i] = 0.008;
            }
        }
    }

    fn get_counts(&self) -> Vec<f64> {
        self.counts.clone()
    }
}

impl Histogram {
    fn create_bins() -> Vec<f64> {
        let mut bins = vec![0.0];

        for exponent in -6..6 {
            for b in 0..200 {
                let bin_value = 10_f64.powf(exponent as f64 + b as f64 / 200.0);
                bins.push(bin_value);
            }
        }

        bins
    }

    fn find_bin(&self, amount: f64) -> Option<usize> {
        let amount_log = amount.log10();
        let percent_in_range = (amount_log - self.first_bin_value) / self.range_bin_values;
        let mut bin_number_est = (percent_in_range * self.bins.len() as f64) as usize;

        while bin_number_est < self.bins.len() && self.bins[bin_number_est] <= amount {
            bin_number_est += 1;
        }

        if bin_number_est > 0 {
            Some(bin_number_est - 1)
        } else {
            None
        }
    }
}
```

**Step 3: Build Python Bindings**

```bash
# Install maturin (Rust → Python build tool)
uv add --dev maturin

# Build Rust module
cd core_rust
uv run maturin develop --release

# Now importable in Python
# from core_rust import Histogram
```

**Step 4: Use in Python (Drop-in Replacement)**

```python
# live/backend/mempool_analyzer.py

# Before (Python):
# from .histogram import Histogram

# After (Rust):
from core_rust import Histogram  # Same interface!

class MempoolAnalyzer:
    def __init__(self):
        self.histogram = Histogram()  # Now 50x faster

    def add_transaction(self, tx):
        for amount in tx.amounts:
            self.histogram.add_amount(amount)  # Same API
```

**Step 5: Benchmark**

```bash
# Python baseline
uv run pytest tests/benchmark_histogram.py --python
# 1,000 tx/sec

# Rust optimized
uv run pytest tests/benchmark_histogram.py --rust
# 50,000 tx/sec (50x speedup!)
```

### Cython Alternative (Simpler)

**If Rust too complex**, use Cython (easier Python → C compilation):

```bash
# Install Cython
uv add --dev cython

# Compile Python to C
cython live/backend/histogram.py --embed

# Build extension
gcc -O3 -shared -fPIC histogram.c -o histogram.so $(python3-config --cflags --ldflags)
```

**Speedup**: 5-10x (less than Rust, but simpler)

**Timeline**: 3-4 weeks (Rust) | 1-2 weeks (Cython)

**Priority**: Low (only if scaling >10k tx/sec)

---

## Feature 3: Redis State Caching

### Motivation

**Problem**: Single-process in-memory state doesn't scale to multiple servers
**Solution**: Redis for shared mempool state

### Architecture

```
Bitcoin Core ZMQ
  ↓
Python Backend #1 ──┐
Python Backend #2 ──┼──> Redis (shared state)
Python Backend #3 ──┘
  ↓
Load Balancer (nginx)
  ↓
Browser Clients
```

### Implementation

**Install Redis**:
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

**Python Redis Client**:
```bash
uv add redis
```

**Modified Mempool State**:
```python
# live/backend/mempool_state_redis.py

import redis
import json
from typing import Dict, List

class MempoolStateRedis:
    """
    Redis-backed mempool state for multi-process deployment.

    Black box interface identical to in-memory version.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.prefix = "mempool:"

    def add_transaction(self, tx: ProcessedTransaction) -> bool:
        """Add transaction to Redis hash"""
        key = f"{self.prefix}tx:{tx.txid}"
        self.redis.hset(key, mapping={
            "amounts": json.dumps(tx.amounts),
            "timestamp": tx.timestamp,
            "fee_rate": tx.fee_rate or 0
        })
        self.redis.expire(key, 10800)  # 3 hours TTL

        return self.redis.sadd(f"{self.prefix}active_txids", tx.txid) == 1

    def remove_transactions(self, txids: List[str]) -> int:
        """Remove confirmed transactions"""
        count = 0
        for txid in txids:
            if self.redis.srem(f"{self.prefix}active_txids", txid):
                self.redis.delete(f"{self.prefix}tx:{txid}")
                count += 1
        return count

    def get_active_transactions(self) -> List[ProcessedTransaction]:
        """Retrieve all active transactions"""
        txids = self.redis.smembers(f"{self.prefix}active_txids")

        transactions = []
        for txid in txids:
            tx_data = self.redis.hgetall(f"{self.prefix}tx:{txid}")
            if tx_data:
                transactions.append(ProcessedTransaction(
                    txid=txid,
                    amounts=json.loads(tx_data["amounts"]),
                    timestamp=float(tx_data["timestamp"]),
                    fee_rate=float(tx_data["fee_rate"])
                ))

        return transactions
```

**Multi-Process Deployment**:
```bash
# Run 3 backend workers
uv run uvicorn live.backend.api:app --port 8001 &
uv run uvicorn live.backend.api:app --port 8002 &
uv run uvicorn live.backend.api:app --port 8003 &

# Nginx load balancer
upstream utxoracle_backends {
    least_conn;
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

server {
    listen 80;

    location /ws/mempool {
        proxy_pass http://utxoracle_backends;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Timeline**: 1-2 weeks

**Priority**: Low (only if >1000 concurrent clients)

---

## Feature 4: Historical Mempool Replay

### Motivation

**Use Cases**:
1. **Algorithm testing** - Validate changes against historical data
2. **Research** - Analyze mempool behavior during events (halvings, ETF launches)
3. **Demo mode** - Show system without live Bitcoin node

### Implementation

**Step 1: Record Mempool**

```python
# live/backend/mempool_recorder.py

import json
import asyncio
from .zmq_listener import stream_mempool_transactions

async def record_mempool(output_file: str, duration_hours: int):
    """
    Record mempool transactions to JSON file.

    Format:
    {"timestamp": 1678901234.5, "raw_hex": "0100000002..."}
    """
    with open(output_file, 'w') as f:
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + duration_hours * 3600

        async for raw_tx in stream_mempool_transactions():
            if asyncio.get_event_loop().time() > end_time:
                break

            record = {
                "timestamp": raw_tx.timestamp,
                "raw_hex": raw_tx.raw_bytes.hex()
            }
            f.write(json.dumps(record) + '\n')
            f.flush()  # Write immediately

# Usage:
# uv run python -m live.backend.mempool_recorder --output mempool_2025-10-18.jsonl --hours 24
```

**Step 2: Replay Mempool**

```python
# live/backend/mempool_replayer.py

import json
import asyncio
from typing import AsyncGenerator
from .models import RawTransaction

async def replay_mempool(input_file: str, speed_multiplier: float = 1.0) -> AsyncGenerator[RawTransaction, None]:
    """
    Replay recorded mempool at original speed or faster.

    Args:
        input_file: Path to recorded mempool
        speed_multiplier: 1.0 = real-time, 10.0 = 10x faster
    """
    with open(input_file, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        record = json.loads(line)

        # Sleep to maintain timing
        if i > 0:
            prev_record = json.loads(lines[i-1])
            time_delta = record["timestamp"] - prev_record["timestamp"]
            await asyncio.sleep(time_delta / speed_multiplier)

        yield RawTransaction(
            raw_bytes=bytes.fromhex(record["raw_hex"]),
            timestamp=record["timestamp"],
            topic='rawtx'
        )

# Usage: Swap in zmq_listener.py
# async def stream_mempool_transactions():
#     async for tx in replay_mempool("mempool_2025-10-18.jsonl", speed_multiplier=10.0):
#         yield tx
```

**Step 3: Historical Dataset**

```bash
# Download pre-recorded mempool (example)
curl -O https://example.com/mempool_recordings/2025-10-18.jsonl.gz
gunzip mempool_2025-10-18.jsonl.gz

# Replay at 10x speed
uv run python -c "
from live.backend.mempool_replayer import replay_mempool
from live.backend.api import app
# ... configure app to use replay ...
"
```

**Timeline**: 1 week

**Priority**: Medium (useful for testing/research)

---

## Feature 5: Multi-Node Deployment

### Motivation

**Requirements**:
- **High Availability** - No single point of failure
- **Load Balancing** - Handle >1000 concurrent clients
- **Geographic Distribution** - Low latency worldwide

### Architecture

```
            ┌─────────────────┐
            │  Load Balancer  │
            │   (Cloudflare)  │
            └────────┬────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼────┐ ┌───▼────┐ ┌───▼────┐
    │  Node   │ │  Node  │ │  Node  │
    │  US-West│ │ US-East│ │  EU    │
    └────┬────┘ └───┬────┘ └───┬────┘
         │          │           │
         └──────────┼───────────┘
                    │
            ┌───────▼────────┐
            │  Redis Cluster │
            │  (shared state)│
            └────────────────┘
```

### Docker Deployment

**Dockerfile**:
```dockerfile
# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock ./
COPY live/ ./live/

# Install dependencies
RUN uv sync --frozen

# Expose WebSocket port
EXPOSE 8000

# Run server
CMD ["uv", "run", "uvicorn", "live.backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend1:
    build: .
    environment:
      - BITCOIN_ZMQ_TX=tcp://bitcoin:28332
      - REDIS_URL=redis://redis:6379
    ports:
      - "8001:8000"
    depends_on:
      - redis

  backend2:
    build: .
    environment:
      - BITCOIN_ZMQ_TX=tcp://bitcoin:28332
      - REDIS_URL=redis://redis:6379
    ports:
      - "8002:8000"
    depends_on:
      - redis

  backend3:
    build: .
    environment:
      - BITCOIN_ZMQ_TX=tcp://bitcoin:28332
      - REDIS_URL=redis://redis:6379
    ports:
      - "8003:8000"
    depends_on:
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend1
      - backend2
      - backend3

volumes:
  redis_data:
```

**Deploy**:
```bash
docker-compose up -d
```

**Timeline**: 2-3 weeks

**Priority**: Low (only if deploying publicly)

---

## Summary

| Feature | Timeline | Complexity | Priority | Benefit |
|---------|----------|------------|----------|---------|
| Three.js WebGL | 2-3 weeks | Medium | Medium | 60fps, 100k points |
| Rust Optimization | 3-4 weeks | High | Low | 10-100x speedup |
| Redis Caching | 1-2 weeks | Low | Low | Multi-process |
| Historical Replay | 1 week | Low | Medium | Testing/research |
| Multi-Node Deploy | 2-3 weeks | Medium | Low | HA, scale |

**Recommendation**: Start with **Historical Replay** (useful for testing) and **Three.js WebGL** (better UX). Only add Rust/Redis if performance bottlenecks proven in production.

---

*Advanced Technical Specification v2.0*
*Last Updated*: 2025-10-18
*Prerequisites*: MVP complete (TECHNICAL_SPEC.md)
