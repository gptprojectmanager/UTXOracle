"""
Unit tests for Whale Flow Detector

TDD Approach: These tests are written BEFORE implementation.
They define the expected behavior of the whale flow detection system.

Test Coverage:
- CSV loading and validation
- Address parsing from transactions
- Transaction classification (inflow/outflow/internal/unrelated)
- Net flow calculation
- Direction determination (ACCUMULATION/DISTRIBUTION/NEUTRAL)
- Signal validation and integrity
"""

import pytest
import json
import csv
from pathlib import Path

# Import will fail initially (RED phase) - this is expected
try:
    from scripts.whale_flow_detector import WhaleFlowDetector
except ImportError:
    WhaleFlowDetector = None

# Import contract from specs directory (add to path if needed)
import sys

specs_contracts_path = Path(
    "/media/sam/1TB/UTXOracle/specs/004-whale-flow-detection/contracts"
)
if str(specs_contracts_path) not in sys.path:
    sys.path.insert(0, str(specs_contracts_path))

from whale_flow_detector_interface import WhaleFlowSignal


# Fixtures
@pytest.fixture
def exchange_addresses_csv():
    """Path to exchange addresses CSV."""
    return "/media/sam/1TB/UTXOracle/data/exchange_addresses.csv"


@pytest.fixture
def exchange_addresses_set(exchange_addresses_csv):
    """Load exchange addresses into a set (O(1) lookup)."""
    addresses = set()
    with open(exchange_addresses_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            addresses.add(row["address"])
    return addresses


@pytest.fixture
def whale_transactions_sample():
    """Load sample transactions from fixtures."""
    fixture_path = Path(
        "/media/sam/1TB/UTXOracle/tests/fixtures/whale_transactions_sample.json"
    )
    with open(fixture_path, "r") as f:
        return json.load(f)


# T016: test_load_exchange_addresses_csv()
def test_load_exchange_addresses_csv(exchange_addresses_csv):
    """
    Test loading exchange addresses from CSV into a set.

    Success Criteria:
    - CSV file loads without errors
    - Returns a set for O(1) lookup
    - Contains expected exchange addresses (10 for MVP)
    - Known addresses (1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX) are present
    """
    if WhaleFlowDetector is None:
        pytest.skip("WhaleFlowDetector not implemented yet (RED phase)")

    detector = WhaleFlowDetector(exchange_addresses_csv)

    # Verify exchange addresses loaded
    address_count = detector.get_exchange_address_count()
    assert address_count > 0, "No exchange addresses loaded"
    assert address_count >= 10, f"Expected at least 10 addresses, got {address_count}"

    # Verify known Binance address is present
    addresses = detector._exchange_addresses
    assert "1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX" in addresses, (
        "Known Binance address not found"
    )


# T017: test_parse_addresses_from_transaction()
def test_parse_addresses_from_transaction(whale_transactions_sample):
    """
    Test extracting input/output addresses from transaction JSON.

    Success Criteria:
    - Correctly parses input addresses from vin[].prevout.scriptpubkey_address
    - Correctly parses output addresses from vout[].scriptpubkey_address
    - Handles missing addresses gracefully (OP_RETURN, coinbase)
    - Returns lists of addresses
    """
    if WhaleFlowDetector is None:
        pytest.skip("WhaleFlowDetector not implemented yet (RED phase)")

    # Test with INFLOW transaction (index 0)
    tx = whale_transactions_sample[0]
    detector = WhaleFlowDetector("/media/sam/1TB/UTXOracle/data/exchange_addresses.csv")

    input_addrs, output_addrs = detector._parse_addresses(tx)

    # Verify parsing
    assert len(input_addrs) == 1, f"Expected 1 input address, got {len(input_addrs)}"
    assert len(output_addrs) == 1, f"Expected 1 output address, got {len(output_addrs)}"
    assert (
        input_addrs[0] == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    )  # Personal wallet (fixed)
    assert output_addrs[0] == "1F1tAaz5x1HUXrCNLbtMDqcw6o5GNn4xqX"  # Binance exchange


# T018: test_classify_transaction_inflow()
def test_classify_transaction_inflow(whale_transactions_sample, exchange_addresses_set):
    """
    Test classification of INFLOW transactions (personal → exchange).

    Success Criteria:
    - Returns flow_type="inflow"
    - Returns direction_multiplier=1 (bearish)
    """
    if WhaleFlowDetector is None:
        pytest.skip("WhaleFlowDetector not implemented yet (RED phase)")

    tx = whale_transactions_sample[0]  # INFLOW example
    detector = WhaleFlowDetector("/media/sam/1TB/UTXOracle/data/exchange_addresses.csv")

    input_addrs, output_addrs = detector._parse_addresses(tx)
    flow_type, multiplier = detector._classify_transaction(input_addrs, output_addrs)

    assert flow_type == "inflow", f"Expected 'inflow', got '{flow_type}'"
    assert multiplier == 1, f"Expected multiplier=1, got {multiplier}"


# T019: test_classify_transaction_outflow()
def test_classify_transaction_outflow(
    whale_transactions_sample, exchange_addresses_set
):
    """
    Test classification of OUTFLOW transactions (exchange → personal).

    Success Criteria:
    - Returns flow_type="outflow"
    - Returns direction_multiplier=-1 (bullish)
    """
    if WhaleFlowDetector is None:
        pytest.skip("WhaleFlowDetector not implemented yet (RED phase)")

    tx = whale_transactions_sample[1]  # OUTFLOW example
    detector = WhaleFlowDetector("/media/sam/1TB/UTXOracle/data/exchange_addresses.csv")

    input_addrs, output_addrs = detector._parse_addresses(tx)
    flow_type, multiplier = detector._classify_transaction(input_addrs, output_addrs)

    assert flow_type == "outflow", f"Expected 'outflow', got '{flow_type}'"
    assert multiplier == -1, f"Expected multiplier=-1, got {multiplier}"


# T020: test_classify_transaction_internal()
def test_classify_transaction_internal(
    whale_transactions_sample, exchange_addresses_set
):
    """
    Test classification of INTERNAL transactions (exchange → exchange).

    Success Criteria:
    - Returns flow_type="internal"
    - Returns direction_multiplier=0 (neutral)
    """
    if WhaleFlowDetector is None:
        pytest.skip("WhaleFlowDetector not implemented yet (RED phase)")

    tx = whale_transactions_sample[2]  # INTERNAL example
    detector = WhaleFlowDetector("/media/sam/1TB/UTXOracle/data/exchange_addresses.csv")

    input_addrs, output_addrs = detector._parse_addresses(tx)
    flow_type, multiplier = detector._classify_transaction(input_addrs, output_addrs)

    assert flow_type == "internal", f"Expected 'internal', got '{flow_type}'"
    assert multiplier == 0, f"Expected multiplier=0, got {multiplier}"


# T021: test_calculate_net_flow()
def test_calculate_net_flow(whale_transactions_sample):
    """
    Test net flow calculation (inflow - outflow) for a block.

    Success Criteria:
    - Correctly sums inflow BTC (personal → exchange)
    - Correctly sums outflow BTC (exchange → personal)
    - Ignores internal transfers (exchange → exchange)
    - Returns net_flow = inflow - outflow
    """
    if WhaleFlowDetector is None:
        pytest.skip("WhaleFlowDetector not implemented yet (RED phase)")

    # Use first 3 transactions: inflow (50.1 BTC), outflow (25.5 BTC), internal (100 BTC)
    detector = WhaleFlowDetector("/media/sam/1TB/UTXOracle/data/exchange_addresses.csv")

    # Mock transaction processing
    test_txs = whale_transactions_sample[:3]
    inflow_btc, outflow_btc, internal_btc = detector._calculate_net_flow(test_txs)

    # Verify calculations (values in satoshis in fixture, converted to BTC)
    assert abs(inflow_btc - 50.1) < 0.1, f"Expected ~50.1 BTC inflow, got {inflow_btc}"
    assert abs(outflow_btc - 25.5) < 0.1, (
        f"Expected ~25.5 BTC outflow, got {outflow_btc}"
    )
    assert abs(internal_btc - 100.0) < 0.1, (
        f"Expected ~100 BTC internal, got {internal_btc}"
    )


# T022: test_determine_direction_accumulation()
def test_determine_direction_accumulation():
    """
    Test direction classification for ACCUMULATION (net outflow > 100 BTC).

    Success Criteria:
    - net_flow < -100 → direction="ACCUMULATION" (bullish)
    """
    if WhaleFlowDetector is None:
        pytest.skip("WhaleFlowDetector not implemented yet (RED phase)")

    detector = WhaleFlowDetector("/media/sam/1TB/UTXOracle/data/exchange_addresses.csv")

    # Simulate large outflow (whales withdrawing)
    net_flow_btc = -150.0  # 150 BTC outflow
    direction = detector._determine_direction(net_flow_btc)

    assert direction == "ACCUMULATION", f"Expected 'ACCUMULATION', got '{direction}'"


# T023: test_determine_direction_distribution()
def test_determine_direction_distribution():
    """
    Test direction classification for DISTRIBUTION (net inflow > 100 BTC).

    Success Criteria:
    - net_flow > 100 → direction="DISTRIBUTION" (bearish)
    """
    if WhaleFlowDetector is None:
        pytest.skip("WhaleFlowDetector not implemented yet (RED phase)")

    detector = WhaleFlowDetector("/media/sam/1TB/UTXOracle/data/exchange_addresses.csv")

    # Simulate large inflow (whales depositing to sell)
    net_flow_btc = 150.0  # 150 BTC inflow
    direction = detector._determine_direction(net_flow_btc)

    assert direction == "DISTRIBUTION", f"Expected 'DISTRIBUTION', got '{direction}'"


# T024: test_determine_direction_neutral()
def test_determine_direction_neutral():
    """
    Test direction classification for NEUTRAL (net flow between -100 and +100 BTC).

    Success Criteria:
    - -100 < net_flow < 100 → direction="NEUTRAL"
    """
    if WhaleFlowDetector is None:
        pytest.skip("WhaleFlowDetector not implemented yet (RED phase)")

    detector = WhaleFlowDetector("/media/sam/1TB/UTXOracle/data/exchange_addresses.csv")

    # Simulate small net flow
    for net_flow in [0, 50, -50, 99, -99]:
        direction = detector._determine_direction(net_flow)
        assert direction == "NEUTRAL", (
            f"Expected 'NEUTRAL' for net_flow={net_flow}, got '{direction}'"
        )


# T025: test_analyze_block_with_mock_data()
def test_analyze_block_with_mock_data(whale_transactions_sample):
    """
    Test full block analysis with mock transaction data.

    Success Criteria:
    - Returns WhaleFlowSignal with all required fields
    - Correctly calculates net_flow_btc
    - Correctly determines direction
    - Confidence score is between 0.0 and 1.0
    """
    if WhaleFlowDetector is None:
        pytest.skip("WhaleFlowDetector not implemented yet (RED phase)")

    detector = WhaleFlowDetector("/media/sam/1TB/UTXOracle/data/exchange_addresses.csv")

    # Mock analyze_block to use fixture data instead of API call
    # (Integration tests will test real API)
    signal = detector._analyze_transactions(
        whale_transactions_sample[:10], block_height=922000, timestamp=1730000000
    )

    # Verify signal structure
    assert isinstance(signal, WhaleFlowSignal), "Should return WhaleFlowSignal instance"
    assert signal.block_height == 922000
    assert signal.timestamp == 1730000000
    assert 0.0 <= signal.confidence <= 1.0, (
        f"Confidence out of range: {signal.confidence}"
    )
    assert signal.direction in ["ACCUMULATION", "DISTRIBUTION", "NEUTRAL"]
    assert signal.tx_count_total == 10
    assert signal.tx_count_relevant > 0


# T026: test_whale_flow_signal_validation()
def test_whale_flow_signal_validation():
    """
    Test WhaleFlowSignal dataclass validation logic.

    Success Criteria:
    - Accepts valid signals
    - Rejects invalid direction values
    - Rejects confidence outside [0.0, 1.0]
    - Validates net_flow = inflow - outflow
    """
    # Valid signal
    valid_signal = WhaleFlowSignal(
        net_flow_btc=50.0,
        direction="DISTRIBUTION",
        confidence=0.75,
        inflow_btc=100.0,
        outflow_btc=50.0,
        internal_btc=200.0,
        tx_count_total=2500,
        tx_count_relevant=320,
        block_height=922000,
        timestamp=1730000000,
    )
    assert valid_signal.direction == "DISTRIBUTION"

    # Invalid direction
    with pytest.raises(ValueError, match="Invalid direction"):
        WhaleFlowSignal(
            net_flow_btc=50.0,
            direction="INVALID",  # Wrong!
            confidence=0.75,
            inflow_btc=100.0,
            outflow_btc=50.0,
            internal_btc=0,
            tx_count_total=100,
            tx_count_relevant=10,
            block_height=922000,
            timestamp=1730000000,
        )

    # Invalid confidence
    with pytest.raises(ValueError, match="Confidence must be between"):
        WhaleFlowSignal(
            net_flow_btc=50.0,
            direction="NEUTRAL",
            confidence=1.5,  # Out of range!
            inflow_btc=100.0,
            outflow_btc=50.0,
            internal_btc=0,
            tx_count_total=100,
            tx_count_relevant=10,
            block_height=922000,
            timestamp=1730000000,
        )

    # Inconsistent net flow
    with pytest.raises(ValueError, match="doesn't match inflow - outflow"):
        WhaleFlowSignal(
            net_flow_btc=999.0,  # Wrong! Should be 100 - 50 = 50
            direction="NEUTRAL",
            confidence=0.5,
            inflow_btc=100.0,
            outflow_btc=50.0,
            internal_btc=0,
            tx_count_total=100,
            tx_count_relevant=10,
            block_height=922000,
            timestamp=1730000000,
        )
