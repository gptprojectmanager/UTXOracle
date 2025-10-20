# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**📘 For Skill Implementation in Other Projects**: See `.claude/SKILLS_FRAMEWORK_BLUEPRINT.md` - Portable meta-framework for implementing Skills in ANY repository.

## Project Overview

UTXOracle is a Bitcoin-native, exchange-free price oracle that calculates the market price of Bitcoin directly from blockchain data. It analyzes on-chain transactions using statistical clustering to derive BTC/USD prices without relying on external exchange APIs.

**Key Principles**:
- Pure Python implementation (no external dependencies beyond standard library)
- Single-file reference implementation for clarity and transparency
- Direct Bitcoin Core RPC connection only
- Privacy-first: no external price feeds

**🎯 Development Philosophy**: KISS (Keep It Simple) + YAGNI (You Ain't Gonna Need It)
→ See [Development Principles](#development-principles) for detailed blueprint

## Running UTXOracle

### Main Script

```bash
# Run for yesterday's price (default)
python3 UTXOracle.py

# Run for specific date
python3 UTXOracle.py -d 2025/10/15

# Use recent 144 blocks
python3 UTXOracle.py -rb

# Specify Bitcoin data directory
python3 UTXOracle.py -p /path/to/bitcoin/data

# View all options
python3 UTXOracle.py -h
```

### Batch Processing

```bash
# Process date range in parallel (12 workers)
python3 scripts/utxoracle_batch.py 2025/10/01 2025/10/10 /home/sam/.bitcoin 12

# Suppress browser opening for batch mode
python3 UTXOracle.py -d 2025/10/17 --no-browser
```

### Requirements

- **Python 3.8+** (standard library only)
- **Bitcoin Core node** (fully synced, RPC enabled)
- **RPC Access**: Either cookie authentication (default) or bitcoin.conf configuration

## Architecture

### Current Implementation (v9.1)

**UTXOracle.py** - Single-file reference implementation using a sequential 12-step algorithm:

1. **Configuration Options** - Parse command-line args, detect OS, set Bitcoin data paths
2. **Establish RPC Connection** - Connect to Bitcoin Core via RPC (cookie or bitcoin.conf auth)
3. **Check Dates** - Validate date input and determine block range
4. **Find Block Hashes** - Retrieve block hashes for analysis window
5. **Initialize Histogram** - Set up data structure for transaction value distribution
6. **Load Histogram from Transaction Data** - Extract and process on-chain transactions
7. **Remove Round Bitcoin Amounts** - Filter out transactions with round BTC amounts (likely non-market activity)
8. **Construct the Price Finding Stencil** - Create statistical clustering framework
9. **Estimate a Rough Price** - Initial price approximation from clustered data
10. **Create Intraday Price Points** - Generate hourly/block-level price estimates
11. **Find the Exact Average Price** - Calculate final volume-weighted median price
12. **Generate a Price Plot HTML Page** - Create interactive visualization with canvas/JavaScript

The code is intentionally verbose and linear (top-to-bottom execution) for educational transparency, not production efficiency.

### Future Architecture Plans

See **MODULAR_ARCHITECTURE.md** and **TECHNICAL_SPEC.md** for planned modular Rust-based architecture:

- **5 independent modules**: Bitcoin Interface, Transaction Processor, Mempool Analyzer, Data Streamer, Visualization Renderer
- **Real-time mempool analysis** with WebGL visualization
- **ZMQ integration** for live transaction streaming
- **Black box principle**: Each module independently replaceable without affecting others

## File Structure

**⚠️ IMPORTANT**: When directory structure changes, update this section immediately.

```
UTXOracle/
├── pyproject.toml            # UV workspace root
├── uv.lock                   # Dependency lockfile (commit this!)
│
├── UTXOracle.py              # Reference implementation v9.1 (IMMUTABLE)
│
├── .claude/                  # Claude Code configuration
│   ├── agents/               # Specialized subagents (6 total)
│   │   ├── bitcoin-onchain-expert.md      # Task 01 - ZMQ listener
│   │   ├── transaction-processor.md       # Task 02 - Binary parsing
│   │   ├── mempool-analyzer.md            # Task 03 - Price estimation
│   │   ├── data-streamer.md               # Task 04 - WebSocket API
│   │   ├── visualization-renderer.md      # Task 05 - Canvas/WebGL
│   │   └── tdd-guard.md                   # TDD enforcement
│   ├── skills/               # Template-driven automation (token efficiency)
│   │   ├── pytest-test-generator/         # Test boilerplate (83% savings)
│   │   ├── github-workflow/               # PR/Issue templates (79% savings)
│   │   ├── pydantic-model-generator/      # Pydantic schema automation (75% savings)
│   │   ├── bitcoin-rpc-connector/         # Bitcoin Core RPC setup (60% savings)
│   │   ├── SKILLS_QUICK_REFERENCE.md      # One-page cheat sheet
│   │   └── SKILLS_ANALYSIS.md             # Skills token economics
│   ├── prompts/
│   │   └── utxoracle-system.md            # Orchestration rules
│   ├── tdd-guard/            # TDD enforcement data
│   │   └── data/             # Coverage reports, test history
│   ├── logs/                 # Claude Code session logs
│   ├── commands/             # Custom slash commands
│   ├── settings.local.json   # Permissions & hooks
│   ├── MCP_OPTIMIZATION.md   # MCP tools configuration guide
│   ├── CONSISTENCY_CHECK.md  # Structure validation report
│   ├── SKILLS_ANALYSIS.md    # Extended Skills analysis
│   └── SKILLS_FRAMEWORK_BLUEPRINT.md  # 📘 META: Portable framework for ANY project
│
├── .serena/                  # Serena MCP (code navigation memory)
│   └── memories/             # Project knowledge base
│
├── .specify/                 # SpecKit (task management) - optional
│   ├── memory/               # Specification memory
│   ├── templates/            # Document templates
│   └── scripts/              # Automation scripts
│
├── core/                     # Shared algorithm modules (FUTURE - not yet created)
│   ├── __init__.py
│   ├── histogram.py          # Steps 5-7 (extracted from UTXOracle.py)
│   ├── stencil.py            # Steps 8-9
│   ├── convergence.py        # Step 11
│   └── bitcoin_rpc.py        # Step 2
│
├── live/                     # Mempool live system (CURRENT IMPLEMENTATION TARGET)
│   ├── backend/              # ✅ Created, ready for implementation
│   │   ├── __init__.py
│   │   ├── zmq_listener.py   # Task 01 - Bitcoin ZMQ interface (TODO)
│   │   ├── mempool_analyzer.py  # Task 03 - Real-time price estimation (TODO)
│   │   ├── api.py            # Task 04 - FastAPI WebSocket server (TODO)
│   │   ├── models.py         # Data models (Pydantic) (TODO)
│   │   └── config.py         # Configuration (TODO)
│   ├── frontend/             # ✅ Created, ready for implementation
│   │   ├── __init__.py
│   │   ├── index.html        # Main page (scaffold created)
│   │   ├── mempool-viz.js    # Canvas 2D renderer (Task 05 MVP) (TODO)
│   │   ├── mempool-viz-webgl.js  # Three.js renderer (Task 05 production) (TODO)
│   │   └── styles.css        # Styling (scaffold created)
│   └── shared/               # ✅ Created
│       ├── __init__.py
│       └── models.py         # Shared data structures (TODO)
│
├── scripts/                  # Utilities
│   ├── utxoracle_batch.py    # Batch processor (parallel date range processing)
│   └── README.md
│
├── docs/                     # Documentation
│   ├── algorithm_concepts.md # Algorithm breakdown by concept
│   ├── tasks/                # Task breakdown for agents
│   │   ├── 00_OVERVIEW.md    # Project overview, agent assignment
│   │   ├── 01_bitcoin_interface.md  # ZMQ listener task
│   │   ├── 02_transaction_processor.md
│   │   ├── 03_mempool_analyzer.md
│   │   ├── 04_data_streamer.md
│   │   └── 05_visualization_renderer.md
│   ├── IMPLEMENTATION_CHECKLIST.md  # Progress tracking
│   ├── api.md                # WebSocket API spec (future)
│   └── deployment.md         # Deployment guide (future)
│
├── tests/                    # ✅ Created, ready for TDD
│   ├── __init__.py
│   ├── conftest.py           # Pytest shared fixtures
│   ├── test_core/            # Core algorithm tests (TODO)
│   │   └── __init__.py
│   ├── test_live/            # Backend tests (TODO)
│   │   └── __init__.py
│   ├── integration/          # End-to-end tests (TODO)
│   │   └── __init__.py
│   └── fixtures/             # Test data (TODO)
│       └── __init__.py
│
├── historical_data/
│   └── html_files/           # 672 HTML files (Dec 15, 2023 → Oct 17, 2025)
│
├── archive/
│   ├── v9/                   # Previous versions
│   ├── v8/
│   ├── v7/
│   └── start9/
│
├── .venv/                    # Python virtual environment (DO NOT COMMIT)
├── .git/                     # Git repository
├── .github/                  # Cleanup automation tools
│   ├── CLEANUP_CHECKLIST.md  # Quick reference for pre-commit cleanup
│   ├── pre-commit.hook       # Optional automated validation hook
│   └── README.md             # How to use cleanup tools
│
├── CLAUDE.md                 # THIS FILE - Claude Code instructions
├── CHANGELOG_SPEC.md         # Formal version evolution (v7→v8→v9→v9.1)
├── MODULAR_ARCHITECTURE.md   # Black box module design
├── TECHNICAL_SPEC.md         # MVP KISS implementation plan
├── TECHNICAL_SPEC_ADVANCED.md  # Production features (WebGL, Rust, etc.)
├── SKILL_SUMMARY.md          # Agent Skills vs Subagents analysis
├── SKILL_SUMMARY_VIDEO_TRANSCRIPT_SUMMARY.md  # Skills video notes (uncommitted)
├── HISTORICAL_DATA.md        # 672 days of historical analysis
└── README.md
```

## Agent & Skill Architecture

### **Subagents** (6) - Complex Reasoning
Specialized agents for deep domain expertise and multi-step workflows.

| Agent | Task | Responsibility | Token Cost |
|-------|------|---------------|-----------|
| bitcoin-onchain-expert | 01 | ZMQ listener, Bitcoin Core integration | ~8,000 |
| transaction-processor | 02 | Binary parsing, UTXOracle filtering | ~7,500 |
| mempool-analyzer | 03 | Histogram, stencil, price estimation | ~9,000 |
| data-streamer | 04 | FastAPI WebSocket server | ~6,000 |
| visualization-renderer | 05 | Canvas 2D + Three.js WebGL | ~7,000 |
| tdd-guard | - | TDD enforcement, coverage validation | ~5,000 |

**Usage**: Invoke via Claude Code for complex implementation tasks.

### **Skills** (4) - Template-Driven Automation
Lightweight templates for repetitive operations with 60-83% token savings.

| Skill | Purpose | Token Savings | Status |
|-------|---------|---------------|--------|
| pytest-test-generator | Auto-generate test boilerplate | 83% (3,000→500) | ✅ |
| github-workflow | PR/Issue/Commit templates | 79% (18,900→4,000) | ✅ |
| pydantic-model-generator | Pydantic data models with validators | 75% (2,000→500) | ✅ |
| bitcoin-rpc-connector | Bitcoin Core RPC client setup | 60% (2,500→1,000) | ✅ |

**Total Skill Savings**: ~20,400 tokens/task (77% reduction on template-driven operations)

**Usage**: Automatically triggered by keywords:
- "generate tests" → pytest-test-generator
- "create PR" → github-workflow
- "pydantic model" → pydantic-model-generator
- "bitcoin rpc" → bitcoin-rpc-connector

### **Modus Operandi**
See `.claude/prompts/utxoracle-system.md` for:
- Task classification rules (01-05)
- TDD workflow enforcement
- Agent spawning patterns
- Checkpoint management
- Error handling protocols

**Combined Token Savings**: ~20,400 tokens/task (Skills) + MCP optimization (~67,200 tokens/pipeline) = **87,600 tokens total**

## Development Principles

### 🎯 KISS & YAGNI Blueprint (ALWAYS REMEMBER!)

#### **KISS** - Keep It Simple, Stupid
- **Choose boring technology**: Python, not Rust (until needed)
- **Avoid premature optimization**: Make it work, then make it fast
- **One module, one purpose**: Each file does ONE thing well
- **Minimize dependencies**: Every dependency is technical debt
- **Clear over clever**: Code that a junior can understand beats "smart" code

#### **YAGNI** - You Ain't Gonna Need It
- **Don't build for hypothetical futures**: Solve TODAY's problem
- **No unused Skills**: 4 Skills are enough (don't add the other 3)
- **No generic solutions**: Specific beats flexible
- **Delete dead code**: If unused for 2 weeks, remove it
- **Resist abstraction temptation**: 3 similar things ≠ need for abstraction

#### **Applied to UTXOracle**
✅ **DO**: Use existing 6 subagents + 4 skills
✅ **DO**: Write simple Python that works
✅ **DO**: Focus on Tasks 01-05 implementation
❌ **DON'T**: Create more Skills "just in case"
❌ **DON'T**: Over-engineer for "future scalability"
❌ **DON'T**: Abstract before you have 3+ real use cases

**Remember**: The best code is no code. The second best is deleted code. The third best is simple code.

---

### Vibe Coding Architecture (Eskil Steenberg)

This project follows "black box" architecture principles for maintainability and AI-assisted development:

1. **Constant developer velocity** - Fast iteration regardless of project size
2. **One module, one person** - Each module can be owned/developed independently
3. **Everything replaceable** - If you don't understand a module, rewrite it without breaking others
4. **Black box interfaces** - Modules communicate only through clean, defined APIs
5. **Write 5 lines today** - Avoid future context switching by writing upfront, not editing later

**Why this matters**: When AI generates complex code, we can easily replace that specific module without touching the rest of the system. Each module is a manageable, bite-sized chunk.

**Reference**: [Eskil Steenberg - Architecting LARGE Software Projects](https://www.youtube.com/watch?v=sSpULGNHyoI)

### Code Philosophy

1. **Transparency over efficiency**: Code is structured for human understanding, not computational optimization
2. **Zero dependencies**: Only Python 3 standard library (reference impl) or minimal deps (live system)
3. **Reproducibility**: Every price calculation is verifiable from public blockchain data
4. **Single file clarity**: UTXOracle.py intentionally avoids function abstraction to keep logic flow visible

### Working with UTXOracle.py

- **Do NOT refactor into functions/classes** unless creating a separate implementation
- **Do NOT add external dependencies** to the reference implementation
- The verbose, repetitive style is intentional for educational purposes
- Code comments with hash tags explain algorithm to non-programmers

### Mempool Live System Development

**Current Status**: Task planning phase (see `docs/tasks/`)

**Tech Stack (KISS MVP)**:
- **Dependency management**: UV (not pip) - 10-100x faster, deterministic lockfiles
- **Backend**: FastAPI + PyZMQ (minimal dependencies)
- **Frontend MVP**: Vanilla JS + Canvas 2D (zero dependencies, no build step)
- **Frontend Production**: Three.js WebGL (only when >5k points cause Canvas lag)
- **Core algorithm**: Pure Python (reuse UTXOracle.py logic exactly)

**Agent Assignment**:
- `bitcoin-onchain-expert`: Task 01 (ZMQ interface)
- `general-purpose`: Tasks 02-05 (processing, analysis, streaming, visualization)

**Development Workflow**:
1. Read task file in `docs/tasks/XX_module_name.md`
2. Launch appropriate agent with task file as context
3. Agent implements module as black box with defined interface
4. Test module independently
5. Integrate with pipeline

**Rust Migration Path** (future):
- Core algorithm (histogram, stencil, convergence) can be rewritten in Rust or Cython
- Replaces Python modules without touching ZMQ/WebSocket/frontend
- Black box interface ensures seamless swap

---

## 🔧 Development Workflow

### TDD Implementation Flow

**Red-Green-Refactor** (when applicable):

1. **🔴 RED**: Write failing test first
   ```bash
   uv run pytest tests/test_module.py  # Should fail
   git add tests/ && git commit -m "TDD RED: Add test for feature X"
   ```

2. **🟢 GREEN**: Minimal code to pass
   ```bash
   # Implement simplest solution
   uv run pytest tests/test_module.py  # Should pass
   git add . && git commit -m "TDD GREEN: Implement feature X"
   ```

3. **♻️ REFACTOR**: Clean up with tests passing
   ```bash
   # Improve code quality
   uv run pytest  # All tests still pass
   git add . && git commit -m "TDD REFACTOR: Clean up feature X"
   ```

**When TDD doesn't fit**: Frontend JS, visualization, exploratory code → Write tests after, document why.

---

### When Stuck Protocol

**CRITICAL**: Maximum **3 attempts** per issue, then STOP.

#### After 3 Failed Attempts:

1. **Document failure**:
   ```markdown
   ## Blocker: [Issue Description]

   **Attempts**:
   1. Tried: [approach] → Failed: [error]
   2. Tried: [approach] → Failed: [error]
   3. Tried: [approach] → Failed: [error]

   **Why stuck**: [hypothesis]
   ```

2. **Research alternatives** (15min max):
   - Find 2-3 similar implementations (GitHub, docs)
   - Note different approaches used
   - Check if problem is already solved differently

3. **Question fundamentals**:
   - Is this the right abstraction level?
   - Can this be split into smaller problems?
   - Is there a simpler approach entirely?
   - Do I need this feature at all? (YAGNI check)

4. **Try different angle OR ask for help**:
   - Different library/framework feature?
   - Remove abstraction instead of adding?
   - Defer to later iteration?

**Never**: Keep trying the same approach >3 times. That's insanity, not persistence.

---

### Decision Framework

When multiple valid approaches exist, choose based on **priority order**:

1. **Testability** → Can I easily test this? (automated, fast, deterministic)
2. **Simplicity** → Is this the simplest solution that works? (KISS)
3. **Consistency** → Does this match existing project patterns?
4. **Readability** → Will someone understand this in 6 months? (Future you)
5. **Reversibility** → How hard to change later? (Prefer reversible)

**Example**:
```python
# ❌ Clever but hard to test
result = reduce(lambda x,y: x|y, map(parse, data), {})

# ✅ Simple, testable, readable
result = {}
for item in data:
    parsed = parse(item)
    result.update(parsed)
```

---

### Error Handling Standards

**Principles**:
- **Fail fast** with descriptive messages
- **Include context** for debugging (not just "Error")
- **Handle at appropriate level** (don't catch everywhere)
- **Never silently swallow** exceptions

**Good Error Messages**:
```python
# ❌ Bad
raise ValueError("Invalid input")

# ✅ Good
raise ValueError(
    f"Bitcoin RPC connection failed: {rpc_url} "
    f"(check bitcoin.conf rpcuser/rpcpassword)"
)
```

**Logging over print**:
```python
# ❌ Bad
print(f"Processing block {height}")  # Lost in production

# ✅ Good
logger.info(f"Processing block {height}", extra={"block_height": height})
```

---

### Test Guidelines

**Principles**:
- Test **behavior**, not implementation
- **One assertion** per test when possible (or closely related assertions)
- **Clear test names** describing scenario: `test_<what>_<when>_<expected>`
- **Use existing fixtures/helpers** (check `tests/conftest.py`)
- Tests must be **deterministic** (no random, no time dependencies)

**Good Test Structure**:
```python
def test_histogram_removes_round_amounts_when_filtering_enabled():
    """Round BTC amounts (1.0, 5.0) should be filtered from histogram."""
    # Arrange
    histogram = {"1.0": 100, "1.23456": 50, "5.0": 200}

    # Act
    filtered = remove_round_amounts(histogram)

    # Assert
    assert "1.0" not in filtered
    assert "5.0" not in filtered
    assert filtered["1.23456"] == 50
```

**Bad Tests**:
```python
# ❌ Testing implementation details
def test_histogram_uses_dict():
    assert isinstance(histogram, dict)  # Who cares?

# ❌ Multiple unrelated assertions
def test_everything():
    assert process() == expected  # Too vague
    assert config.loaded  # Unrelated
    assert server.running  # Unrelated
```

---

### Important Reminders

#### ❌ **NEVER**:
- Use `--no-verify` to bypass commit hooks (fix the issue instead)
- Disable tests instead of fixing them (broken tests = broken code)
- Commit code that doesn't compile/run
- Use `print()` for logging (use `logging` module)
- Hardcode secrets/API keys (use `.env`)
- Commit without testing locally first

#### ✅ **ALWAYS**:
- Run tests before committing (`uv run pytest`)
- Format/lint before committing (`ruff check . && ruff format .`)
- Write commit message explaining **WHY** (not just what)
- Update relevant docs when changing behavior
- Check `.gitignore` before committing sensitive files
- Use `uv` for dependencies (not `pip`)

---

## 🧹 Task Completion Protocol

**IMPORTANT**: Run this checklist BEFORE marking any task as complete or creating a commit.

### ✅ Pre-Commit Cleanup Checklist

When completing a task, **ALWAYS** do the following cleanup:

#### 1. Remove Temporary Files
```bash
# Check for temporary files
find . -type f \( -name "*.tmp" -o -name "*.bak" -o -name "*~" -o -name "*.swp" \)

# Remove if found (review first!)
# find . -type f \( -name "*.tmp" -o -name "*.bak" -o -name "*~" \) -delete
```

#### 2. Clean Python Cache
```bash
# Remove Python cache (auto-regenerates)
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
```

#### 3. Remove Debug/Test Outputs
```bash
# Check for test artifacts
ls -la *.html *.json *.log 2>/dev/null | grep -v "UTXOracle_"

# Move to archive if historical data, delete if temporary
```

#### 4. Code Cleanup (Manual Review)

**Remove**:
- ❌ Commented-out code blocks (if >1 week old)
- ❌ `print()` debug statements
- ❌ Unused imports (`ruff check --select F401`)
- ❌ TODO comments that are now resolved
- ❌ Dead functions/classes (never called)

**Fix**:
- ✅ Run linter: `ruff check .` (if available)
- ✅ Format code: `ruff format .` (if available)
- ✅ Type hints: Add where missing

#### 5. Documentation Cleanup

**Consolidate**:
- ❌ Delete draft `.md` files not referenced anywhere
- ❌ Remove obsolete documentation
- ✅ Update CLAUDE.md if structure changed
- ✅ Update relevant task files in `docs/tasks/`

**Check**:
```bash
# Find unreferenced markdown files
find docs -name "*.md" -type f

# Review each - is it still needed?
```

#### 6. Git Status Review

```bash
# Check what's about to be committed
git status

# Review untracked files - keep or delete?
git status --short | grep "^??"

# Check for large files (>1MB)
find . -type f -size +1M -not -path "./.git/*" -not -path "./historical_data/*"
```

#### 7. Update .gitignore (If Needed)

If you find temporary files that shouldn't be committed:
```bash
# Add patterns to .gitignore
echo "*.tmp" >> .gitignore
echo "debug_*.log" >> .gitignore
echo ".DS_Store" >> .gitignore
```

---

### 🚨 Before Every Commit

**Mandatory checks** (MUST pass before committing):

```bash
# 1. No uncommitted temporary files
[ -z "$(find . -name '*.tmp' -o -name '*.bak')" ] && echo "✅ No temp files" || echo "❌ Temp files found"

# 2. Tests pass (if applicable)
# uv run pytest tests/ && echo "✅ Tests pass" || echo "❌ Tests fail"

# 3. No obvious debug code
! git diff --cached | grep -E "(print\(|console\.log|debugger|import pdb)" && echo "✅ No debug code" || echo "⚠️  Debug code in commit"

# 4. File count reasonable
CHANGED=$(git diff --cached --name-only | wc -l)
[ $CHANGED -lt 20 ] && echo "✅ Changed files: $CHANGED" || echo "⚠️  Many files: $CHANGED (review needed)"
```

---

### 🗑️ What to DELETE vs KEEP

#### ❌ DELETE (Always)
- Temporary files (`.tmp`, `.bak`, `~`)
- Python cache (`__pycache__`, `.pyc`)
- Test cache (`.pytest_cache`, `.coverage`)
- Debug logs (`debug_*.log`, `*.trace`)
- Screenshots for debugging (unless documented)
- Experiment files not integrated (`test_*.py` outside tests/)
- Commented code blocks >1 week old
- Unused imports
- TODOs marked DONE

#### ✅ KEEP (Always)
- Historical data (`historical_data/html_files/`)
- Documentation (if referenced in CLAUDE.md or README)
- Tests (`tests/**/*.py`)
- Configuration files (`.claude/`, `pyproject.toml`, `.gitignore`)
- Source code in `live/`, `core/`, `scripts/`
- `uv.lock` (dependency lockfile - COMMIT THIS!)

#### ⚠️ REVIEW CASE-BY-CASE
- Jupyter notebooks (`.ipynb`) - Keep if documented, archive if experimental
- Large binary files (>1MB) - Consider git LFS or external storage
- Generated HTML files - Keep if part of output, delete if test artifacts
- Log files - Keep if needed for debugging, delete if >1 week old

---

### 📝 Post-Cleanup Commit Message

After cleanup, commit with clear message:

```bash
# Good commit message pattern:
git commit -m "[Task XX] Module: Description

Changes:
- Implemented: feature.py
- Tests: test_feature.py (coverage: 85%)
- Cleanup: Removed 3 temp files, 2 unused imports

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### 🔄 Periodic Cleanup (Weekly)

Run this every Friday or after completing a major task:

```bash
# Find files not modified in 2 weeks
find . -type f -mtime +14 -not -path "./.git/*" -not -path "./historical_data/*"

# Review and archive or delete
```

**Check for**:
- Orphaned files (not referenced anywhere)
- Old experiment branches (`git branch --merged`)
- Unused Skills (check usage in logs)
- Outdated documentation

---

### 🎯 Cleanup Automation (Optional)

Create `.git/hooks/pre-commit` for automatic checks:

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "🧹 Running pre-commit cleanup..."

# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Check for temp files
TEMP_FILES=$(find . -name "*.tmp" -o -name "*.bak" 2>/dev/null)
if [ -n "$TEMP_FILES" ]; then
    echo "❌ Temporary files found:"
    echo "$TEMP_FILES"
    echo "Remove them before committing"
    exit 1
fi

# Check for debug code
if git diff --cached | grep -E "(print\(|console\.log|debugger)"; then
    echo "⚠️  Debug code detected in staged files"
    echo "Review and remove before committing (or use --no-verify to skip)"
    # Don't block commit, just warn
fi

echo "✅ Pre-commit checks passed"
```

---

## Bitcoin Node Connection

UTXOracle connects to Bitcoin Core using:

1. **Cookie authentication** (default): Reads `.cookie` file from Bitcoin data directory
2. **bitcoin.conf settings**: If RPC credentials are configured

Default Bitcoin data paths:
- **Linux**: `~/.bitcoin`
- **macOS**: `~/Library/Application Support/Bitcoin`
- **Windows**: `%APPDATA%\Bitcoin`

Required bitcoin.conf settings for future ZMQ features:
```conf
zmqpubhashtx=tcp://127.0.0.1:28332
zmqpubrawblock=tcp://127.0.0.1:28333
zmqpubrawtx=tcp://127.0.0.1:28332
rpcuser=<user>
rpcpassword=<password>
rpcallowip=127.0.0.1
```

## Historical Data

The repository includes 672 days of historical analysis (Dec 15, 2023 → Oct 17, 2025) as HTML files in `historical_data/html_files/`. Each file contains:

- Daily BTC/USD price calculation
- Statistical confidence score
- Transaction histogram analysis
- Intraday price evolution
- Interactive visualizations
- Blockchain metadata

Processing stats: 99.85% success rate, ~2.25 seconds per date with 12 parallel workers.

## Output

UTXOracle generates:
- **Console output**: Date and calculated price (e.g., "2025-10-15 price: $111,652")
- **HTML file**: Interactive visualization saved as `UTXOracle_YYYY-MM-DD.html`
- **Auto-opens browser**: Unless `--no-browser` flag is used

## Testing & Verification

All results are reproducible:
```bash
# Verify specific historical date
python3 UTXOracle.py -d 2025/10/15

# Should output: $111,652
```

Compare against historical_data files to verify algorithm consistency.

## License

Blue Oak Model License 1.0.0 - permissive open-source license designed for simplicity and developer freedom.
