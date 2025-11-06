"""
Whale Flow Backtest - Historical Validation

Analyzes historical blocks to validate whale flow correlation with price movements.

Usage:
    python3 whale_flow_backtest.py --days 1 --csv data/exchange_addresses.csv
    python3 whale_flow_backtest.py --start-block 920000 --end-block 920144

Success Criteria (from spec.md):
- SC-002: Correlation >0.6 on 7-day backtest
- SC-003: False positive rate <20%

Performance Warning:
- Sequential processing: ~3 minutes per block (electrs HTTP API)
- 1 day (144 blocks) = ~7 hours
- 7 days (1,008 blocks) = ~50 hours
- Consider running overnight or with reduced sample size

References:
- specs/004-whale-flow-detection/spec.md (SC-002, SC-003)
- scripts/whale_flow_detector.py (WhaleFlowDetector class)
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Import whale detector
from whale_flow_detector import WhaleFlowDetector

# Import contract
specs_contracts_path = (
    Path(__file__).parent.parent / "specs" / "004-whale-flow-detection" / "contracts"
)
if str(specs_contracts_path) not in sys.path:
    sys.path.insert(0, str(specs_contracts_path))

from whale_flow_detector_interface import WhaleFlowSignal


# Configuration
ELECTRS_API_URL = "http://localhost:3001"
BLOCKS_PER_DAY = 144  # Bitcoin: ~10 minutes per block = 144 blocks/day

logger = logging.getLogger(__name__)


def calculate_block_range(
    days: int = None, start_block: int = None, end_block: int = None
) -> Tuple[int, int]:
    """
    T068-T069: Calculate block range for backtest.

    Args:
        days: Number of days to backtest (if provided, uses latest blocks)
        start_block: Custom start block height
        end_block: Custom end block height

    Returns:
        Tuple of (start_block, end_block)

    Raises:
        ValueError: If arguments are invalid
    """
    import requests

    # Validate arguments
    if days and (start_block or end_block):
        raise ValueError("Cannot use --days with --start-block/--end-block")

    if days:
        # T069: Calculate range from latest block
        response = requests.get(f"{ELECTRS_API_URL}/blocks/tip/height", timeout=10)
        response.raise_for_status()
        latest_height = int(response.text.strip())

        num_blocks = days * BLOCKS_PER_DAY
        start = latest_height - num_blocks
        end = latest_height

        logger.info(f"📅 Backtest range: {days} days ({num_blocks} blocks)")
        logger.info(f"   Start: block {start}")
        logger.info(f"   End: block {end}")

        return start, end

    elif start_block and end_block:
        # Custom range
        if end_block <= start_block:
            raise ValueError("end_block must be greater than start_block")

        num_blocks = end_block - start_block
        logger.info(f"📅 Custom block range: {num_blocks} blocks")
        logger.info(f"   Start: block {start_block}")
        logger.info(f"   End: block {end_block}")

        return start_block, end_block

    else:
        raise ValueError("Must provide either --days or --start-block + --end-block")


async def analyze_block_range(
    whale_detector: WhaleFlowDetector, start_block: int, end_block: int
) -> List[WhaleFlowSignal]:
    """
    T070: Analyze whale flow for a range of blocks (ASYNC with aiohttp).

    Args:
        whale_detector: Initialized WhaleFlowDetector instance
        start_block: Start block height
        end_block: End block height (exclusive)

    Returns:
        List of WhaleFlowSignal objects

    Note:
        OPTIMIZED with async/await: ~3-5 seconds per block (was ~180 seconds).
        Progress is logged every 10 blocks.
    """
    signals = []
    total_blocks = end_block - start_block

    logger.info("🔍 Starting backtest analysis...")
    logger.info(f"   Total blocks: {total_blocks}")
    logger.info(f"   Estimated time: {total_blocks * 5 / 60:.1f} hours (async)")
    logger.info("   Progress logged every 10 blocks")

    for i, height in enumerate(range(start_block, end_block), start=1):
        try:
            # Analyze block (now async)
            signal = await whale_detector.analyze_block(height)
            signals.append(signal)

            # Log progress every 10 blocks
            if i % 10 == 0 or i == 1:
                pct = (i / total_blocks) * 100
                elapsed = i * 5 / 60  # Rough estimate: 5 sec/block
                remaining = (total_blocks - i) * 5 / 60
                logger.info(
                    f"   [{i}/{total_blocks}] ({pct:.1f}%) - "
                    f"Block {height}: {signal.direction} "
                    f"({signal.net_flow_btc:+.1f} BTC) - "
                    f"Elapsed: {elapsed:.1f}h, Remaining: {remaining:.1f}h"
                )

        except Exception as e:
            logger.warning(f"   ⚠️  Block {height} failed: {e}. Skipping...")
            continue

    logger.info(f"✅ Analysis complete: {len(signals)}/{total_blocks} blocks processed")
    return signals


def calculate_correlation(
    signals: List[WhaleFlowSignal], price_changes: List[float]
) -> float:
    """
    T074: Calculate Pearson correlation between whale net flow and 24h price change.

    Args:
        signals: List of WhaleFlowSignal objects
        price_changes: List of 24h price changes (in %, aligned with signals)

    Returns:
        Pearson correlation coefficient (-1.0 to 1.0)

    Note:
        Uses numpy if available, otherwise falls back to manual calculation.
    """
    if len(signals) != len(price_changes):
        raise ValueError(
            f"Signal count ({len(signals)}) != price change count ({len(price_changes)})"
        )

    if len(signals) < 2:
        logger.warning("Not enough data points for correlation (need at least 2)")
        return 0.0

    # Extract net flows
    net_flows = [s.net_flow_btc for s in signals]

    # Try numpy for efficiency
    try:
        import numpy as np

        corr = np.corrcoef(net_flows, price_changes)[0, 1]
        return float(corr) if not np.isnan(corr) else 0.0
    except ImportError:
        # Manual Pearson correlation
        n = len(net_flows)
        mean_flow = sum(net_flows) / n
        mean_price = sum(price_changes) / n

        numerator = sum(
            (net_flows[i] - mean_flow) * (price_changes[i] - mean_price)
            for i in range(n)
        )
        denom_flow = sum((x - mean_flow) ** 2 for x in net_flows) ** 0.5
        denom_price = sum((x - mean_price) ** 2 for x in price_changes) ** 0.5

        if denom_flow == 0 or denom_price == 0:
            return 0.0

        return numerator / (denom_flow * denom_price)


def calculate_false_positive_rate(
    signals: List[WhaleFlowSignal], price_changes: List[float]
) -> float:
    """
    T075: Calculate false positive rate for whale signals.

    Definition:
    - False positive: Signal predicts wrong direction
    - ACCUMULATION (bullish) but price goes down (negative change)
    - DISTRIBUTION (bearish) but price goes up (positive change)
    - NEUTRAL signals are excluded from calculation

    Args:
        signals: List of WhaleFlowSignal objects
        price_changes: List of 24h price changes (in %, aligned with signals)

    Returns:
        False positive rate (0.0 to 1.0)
    """
    if len(signals) != len(price_changes):
        raise ValueError(
            f"Signal count ({len(signals)}) != price change count ({len(price_changes)})"
        )

    false_positives = 0
    total_signals = 0

    for signal, price_change in zip(signals, price_changes):
        # Skip NEUTRAL signals (not actionable)
        if signal.direction == "NEUTRAL":
            continue

        total_signals += 1

        # Check if prediction was wrong
        if signal.direction == "ACCUMULATION" and price_change < 0:
            false_positives += 1  # Predicted bullish but price dropped
        elif signal.direction == "DISTRIBUTION" and price_change > 0:
            false_positives += 1  # Predicted bearish but price rose

    if total_signals == 0:
        logger.warning("No actionable signals (all NEUTRAL)")
        return 0.0

    return false_positives / total_signals


def main():
    """
    T066-T067: Main CLI for whale flow backtest.
    """
    parser = argparse.ArgumentParser(
        description="Whale Flow Backtest - Validate correlation with price movements"
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Number of days to backtest (from latest block)",
    )
    parser.add_argument(
        "--start-block",
        type=int,
        help="Custom start block height",
    )
    parser.add_argument(
        "--end-block",
        type=int,
        help="Custom end block height",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="/media/sam/1TB/UTXOracle/data/exchange_addresses.csv",
        help="Path to exchange addresses CSV",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="backtest_results.json",
        help="Output file for results (JSON format)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Validate arguments
    if not args.days and not (args.start_block and args.end_block):
        parser.error("Must provide either --days or --start-block + --end-block")

    if args.days and (args.start_block or args.end_block):
        parser.error("Cannot use --days with --start-block/--end-block")

    logger.info("🐋 Whale Flow Backtest Starting...")
    logger.info(f"   Exchange addresses: {args.csv}")

    # Initialize whale detector
    whale_detector = WhaleFlowDetector(args.csv)
    logger.info(
        f"   ✅ Whale detector initialized ({whale_detector.get_exchange_address_count()} addresses)"
    )

    # Calculate block range
    try:
        start_block, end_block = calculate_block_range(
            days=args.days, start_block=args.start_block, end_block=args.end_block
        )
    except Exception as e:
        logger.error(f"❌ Failed to calculate block range: {e}")
        sys.exit(1)

    # Analyze blocks (async with aiohttp)
    logger.info("")
    import asyncio

    signals = asyncio.run(analyze_block_range(whale_detector, start_block, end_block))

    if len(signals) == 0:
        logger.error("❌ No blocks analyzed successfully")
        sys.exit(1)

    # TODO T072-T073: Fetch price data and calculate 24h price changes
    # For now, we just save the whale signals
    logger.info("")
    logger.info("📊 Backtest Results:")
    logger.info(f"   Blocks analyzed: {len(signals)}")
    logger.info(
        f"   ACCUMULATION signals: {sum(1 for s in signals if s.direction == 'ACCUMULATION')}"
    )
    logger.info(
        f"   DISTRIBUTION signals: {sum(1 for s in signals if s.direction == 'DISTRIBUTION')}"
    )
    logger.info(
        f"   NEUTRAL signals: {sum(1 for s in signals if s.direction == 'NEUTRAL')}"
    )
    logger.info(
        f"   Average net flow: {sum(s.net_flow_btc for s in signals) / len(signals):+.2f} BTC"
    )

    # Save results
    results = {
        "metadata": {
            "start_block": start_block,
            "end_block": end_block,
            "blocks_analyzed": len(signals),
            "timestamp": datetime.now().isoformat(),
        },
        "signals": [
            {
                "block_height": s.block_height,
                "net_flow_btc": s.net_flow_btc,
                "direction": s.direction,
                "confidence": s.confidence,
                "inflow_btc": s.inflow_btc,
                "outflow_btc": s.outflow_btc,
                "internal_btc": s.internal_btc,
                "tx_count_total": s.tx_count_total,
                "tx_count_relevant": s.tx_count_relevant,
            }
            for s in signals
        ],
    }

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"   💾 Results saved to: {args.output}")
    logger.info("")
    logger.info("✅ Backtest complete!")
    logger.info("")
    logger.info("⚠️  TODO: Price correlation analysis (T072-T076) not yet implemented")
    logger.info("   Next steps:")
    logger.info("   1. Fetch BTC/USD prices for each block")
    logger.info("   2. Calculate 24h price changes")
    logger.info("   3. Calculate correlation (target: >0.6)")
    logger.info("   4. Calculate false positive rate (target: <20%)")


if __name__ == "__main__":
    main()
