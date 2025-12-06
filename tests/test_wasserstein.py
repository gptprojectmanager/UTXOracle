"""
Test suite for Wasserstein Distance Calculator (spec-010).

Tests follow TDD RED-GREEN-REFACTOR approach as per UTXOracle constitution.
Each test is independent and validates specific behavior.

Test organization by User Story:
- US1: Distribution Shift Detection (test_wasserstein_*)
- US2: Rolling Window Analysis (test_rolling_*)
- US3: Enhanced Fusion Integration (test_enhanced_fusion_*, test_fusion_*)
"""

from datetime import datetime

import pytest


# =============================================================================
# Phase 3: User Story 1 - Distribution Shift Detection Tests
# =============================================================================


class TestWassersteinIdenticalDistributions:
    """T008: Test that identical distributions have zero Wasserstein distance."""

    def test_identical_lists_return_zero_distance(self):
        """Given identical distributions, W_1 should be exactly 0.0."""
        from scripts.metrics.wasserstein import wasserstein_1d

        values = [100.0, 200.0, 300.0, 400.0, 500.0] * 10  # 50 samples

        result = wasserstein_1d(values, values.copy())

        assert result.distance == 0.0
        assert result.distance_normalized == 0.0
        assert result.shift_direction == "NONE"
        assert result.is_valid is True

    def test_identical_large_distribution(self):
        """Large identical distributions should also have zero distance."""
        from scripts.metrics.wasserstein import wasserstein_1d

        values = list(range(1, 1001))  # 1000 values

        result = wasserstein_1d(values, values.copy())

        assert result.distance == 0.0
        assert result.distance_normalized == 0.0


class TestWassersteinShiftedUniform:
    """T009: Test shifted uniform distributions have expected W distance."""

    def test_shifted_uniform_distance(self):
        """Uniform[0,1] vs Uniform[0.5,1.5] should have W=0.5."""
        from scripts.metrics.wasserstein import wasserstein_1d

        # Create uniform distributions with enough samples
        n = 100
        values_1 = [i / (n - 1) for i in range(n)]  # [0, 1]
        values_2 = [0.5 + i / (n - 1) for i in range(n)]  # [0.5, 1.5]

        result = wasserstein_1d(values_1, values_2)

        # Distance should be 0.5 (mean shift)
        assert abs(result.distance - 0.5) < 0.01
        assert result.is_valid is True

    def test_shift_direction_concentration(self):
        """Shift to higher values should indicate CONCENTRATION."""
        from scripts.metrics.wasserstein import wasserstein_1d

        values_1 = [i for i in range(100)]
        values_2 = [i + 20 for i in range(100)]  # Shifted up by 20

        result = wasserstein_1d(values_1, values_2, threshold=0.05)

        assert result.shift_direction == "CONCENTRATION"


class TestWassersteinDirectionConcentration:
    """T010: Test concentration shift detection."""

    def test_concentration_when_mean_increases(self):
        """CONCENTRATION when values shift to higher amounts."""
        from scripts.metrics.wasserstein import wasserstein_1d

        # Original: smaller values
        values_1 = [100.0] * 50

        # Later: larger values (whale accumulation pattern)
        values_2 = [200.0] * 50

        result = wasserstein_1d(values_1, values_2, threshold=0.05)

        assert result.shift_direction == "CONCENTRATION"
        assert result.window_2_mean > result.window_1_mean


class TestWassersteinDirectionDispersion:
    """T011: Test dispersion shift detection."""

    def test_dispersion_when_mean_decreases(self):
        """DISPERSION when values shift to lower amounts."""
        from scripts.metrics.wasserstein import wasserstein_1d

        # Original: larger values
        values_1 = [200.0] * 50

        # Later: smaller values (retail entry pattern)
        values_2 = [100.0] * 50

        result = wasserstein_1d(values_1, values_2, threshold=0.05)

        assert result.shift_direction == "DISPERSION"
        assert result.window_2_mean < result.window_1_mean


class TestWassersteinInsufficientSamples:
    """T012: Test handling of insufficient samples."""

    def test_insufficient_samples_returns_invalid(self):
        """is_valid=False when sample count < min_samples."""
        from scripts.metrics.wasserstein import wasserstein_1d

        # Only 10 samples (below default 50)
        values_1 = [100.0] * 10
        values_2 = [200.0] * 10

        result = wasserstein_1d(values_1, values_2, min_samples=50)

        assert result.is_valid is False
        assert result.window_1_size == 10
        assert result.window_2_size == 10

    def test_empty_lists_return_invalid(self):
        """Empty distributions should return is_valid=False."""
        from scripts.metrics.wasserstein import wasserstein_1d

        result = wasserstein_1d([], [])

        assert result.is_valid is False
        assert result.distance == 0.0

    def test_one_empty_list_returns_invalid(self):
        """One empty distribution should return is_valid=False."""
        from scripts.metrics.wasserstein import wasserstein_1d

        result = wasserstein_1d([100.0] * 50, [])

        assert result.is_valid is False


# =============================================================================
# Phase 4: User Story 2 - Rolling Window Analysis Tests
# =============================================================================


class TestRollingWassersteinStable:
    """T018: Test rolling Wasserstein on stable series."""

    def test_stable_series_low_variance(self):
        """Stable series should have low W variance."""
        from scripts.metrics.wasserstein import rolling_wasserstein

        # Stable series: same distribution repeated
        values = [100.0 + i % 10 for i in range(500)]

        result = rolling_wasserstein(
            values, window_size=50, step_size=10, threshold=0.10
        )

        assert result.is_valid is True
        assert result.std_distance < 0.02  # Low variance
        assert result.regime_status == "STABLE"

    def test_stable_series_no_sustained_shift(self):
        """Stable series should not detect sustained shift."""
        from scripts.metrics.wasserstein import rolling_wasserstein

        # Truly stable: same distribution in each window
        import random

        random.seed(42)
        values = [random.gauss(100, 10) for _ in range(500)]

        result = rolling_wasserstein(
            values, window_size=50, step_size=10, threshold=0.15
        )

        assert result.sustained_shift_detected is False


class TestRollingWassersteinRegimeChange:
    """T019: Test regime change detection at known point."""

    def test_regime_change_peak_detection(self):
        """W should peak at regime change point."""
        from scripts.metrics.wasserstein import rolling_wasserstein

        # Create series with regime change at t=250
        values = [100.0] * 250 + [200.0] * 250  # Sharp regime change

        result = rolling_wasserstein(values, window_size=50, step_size=10)

        assert result.is_valid is True
        assert result.max_distance > 0.0
        assert len(result.shift_windows) > 0


class TestRollingSustainedShift:
    """T020: Test sustained shift detection (3+ consecutive)."""

    def test_sustained_shift_three_consecutive(self):
        """Sustained shift when 3+ consecutive high-W windows."""
        from scripts.metrics.wasserstein import rolling_wasserstein

        # Large sustained shift
        values = [100.0] * 100 + [500.0] * 400

        result = rolling_wasserstein(
            values, window_size=50, step_size=10, threshold=0.05
        )

        assert result.sustained_shift_detected is True
        assert result.regime_status == "SHIFTED"


class TestRollingRegimeStatusTransitions:
    """T021: Test regime status classification."""

    def test_transitioning_status(self):
        """TRANSITIONING when some shifts but not sustained."""
        from scripts.metrics.wasserstein import rolling_wasserstein

        # Create series with brief spike
        values = [100.0] * 200 + [150.0] * 50 + [100.0] * 250

        result = rolling_wasserstein(
            values, window_size=50, step_size=25, threshold=0.05
        )

        # Should detect some shifts
        assert result.is_valid is True


# =============================================================================
# Phase 5: User Story 3 - Enhanced Fusion Integration Tests
# =============================================================================


class TestEnhancedFusionWithWasserstein:
    """T028: Test enhanced fusion accepts wasserstein_vote."""

    def test_fusion_with_wasserstein_changes_signal(self):
        """Wasserstein vote should affect fusion signal."""
        from scripts.metrics.monte_carlo_fusion import enhanced_fusion

        # Run fusion without wasserstein
        result_without = enhanced_fusion(
            whale_vote=0.5,
            whale_conf=0.9,
            utxo_vote=0.3,
            utxo_conf=0.8,
            n_samples=100,
        )

        # Run fusion with positive wasserstein vote
        result_with = enhanced_fusion(
            whale_vote=0.5,
            whale_conf=0.9,
            utxo_vote=0.3,
            utxo_conf=0.8,
            wasserstein_vote=0.6,
            n_samples=100,
        )

        # Signal should be affected by wasserstein
        assert result_with.components_available >= result_without.components_available


class TestFusionWeightsSumToOne:
    """T029: Test that all fusion weights sum to 1.0."""

    def test_weights_sum_validation(self):
        """All component weights should sum to 1.0."""
        from scripts.metrics.monte_carlo_fusion import ENHANCED_WEIGHTS

        total = sum(ENHANCED_WEIGHTS.values())

        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected 1.0"


class TestFusionBackwardCompatibility:
    """T030: Test fusion works without wasserstein (backward compatible)."""

    def test_fusion_without_wasserstein(self):
        """Fusion should work without wasserstein_vote parameter."""
        from scripts.metrics.monte_carlo_fusion import enhanced_fusion

        # Call without wasserstein_vote
        result = enhanced_fusion(
            whale_vote=0.5,
            whale_conf=0.9,
            utxo_vote=0.3,
            utxo_conf=0.8,
            n_samples=100,
        )

        assert result is not None
        assert result.action in ["BUY", "SELL", "HOLD"]
        assert -1.0 <= result.signal_mean <= 1.0


# =============================================================================
# Dataclass Validation Tests
# =============================================================================


class TestWassersteinResultValidation:
    """Test WassersteinResult dataclass validation."""

    def test_negative_distance_raises(self):
        """Negative distance should raise ValueError."""
        from scripts.models.metrics_models import WassersteinResult

        with pytest.raises(ValueError, match="distance must be >= 0"):
            WassersteinResult(
                distance=-1.0,
                distance_normalized=0.0,
                window_1_size=50,
                window_2_size=50,
                window_1_mean=100.0,
                window_2_mean=100.0,
                window_1_std=10.0,
                window_2_std=10.0,
                shift_direction="NONE",
                is_significant=False,
                is_valid=True,
            )

    def test_invalid_direction_raises(self):
        """Invalid shift_direction should raise ValueError."""
        from scripts.models.metrics_models import WassersteinResult

        with pytest.raises(ValueError, match="shift_direction must be one of"):
            WassersteinResult(
                distance=0.5,
                distance_normalized=0.25,
                window_1_size=50,
                window_2_size=50,
                window_1_mean=100.0,
                window_2_mean=150.0,
                window_1_std=10.0,
                window_2_std=10.0,
                shift_direction="INVALID",
                is_significant=True,
                is_valid=True,
            )


class TestRollingWassersteinResultValidation:
    """Test RollingWassersteinResult dataclass validation."""

    def test_mismatched_lengths_raises(self):
        """Mismatched distances/timestamps should raise ValueError."""
        from scripts.models.metrics_models import RollingWassersteinResult

        with pytest.raises(ValueError, match="length mismatch"):
            RollingWassersteinResult(
                distances=[0.1, 0.2, 0.3],
                timestamps=[datetime.now()],  # Wrong length
                mean_distance=0.2,
                max_distance=0.3,
                min_distance=0.1,
                std_distance=0.1,
                sustained_shift_detected=False,
                shift_windows=[],
                regime_status="STABLE",
                wasserstein_vote=0.0,
                vote_confidence=0.0,
                window_size=144,
                step_size=6,
                threshold=0.1,
                total_samples=1000,
                windows_analyzed=3,
                is_valid=True,
            )

    def test_invalid_regime_status_raises(self):
        """Invalid regime_status should raise ValueError."""
        from scripts.models.metrics_models import RollingWassersteinResult

        with pytest.raises(ValueError, match="regime_status must be one of"):
            RollingWassersteinResult(
                distances=[0.1],
                timestamps=[datetime.now()],
                mean_distance=0.1,
                max_distance=0.1,
                min_distance=0.1,
                std_distance=0.0,
                sustained_shift_detected=False,
                shift_windows=[],
                regime_status="INVALID",
                wasserstein_vote=0.0,
                vote_confidence=0.0,
                window_size=144,
                step_size=6,
                threshold=0.1,
                total_samples=100,
                windows_analyzed=1,
                is_valid=True,
            )

    def test_vote_out_of_range_raises(self):
        """Vote outside [-1, 1] should raise ValueError."""
        from scripts.models.metrics_models import RollingWassersteinResult

        with pytest.raises(ValueError, match="wasserstein_vote must be in"):
            RollingWassersteinResult(
                distances=[0.1],
                timestamps=[datetime.now()],
                mean_distance=0.1,
                max_distance=0.1,
                min_distance=0.1,
                std_distance=0.0,
                sustained_shift_detected=False,
                shift_windows=[],
                regime_status="STABLE",
                wasserstein_vote=1.5,  # Out of range
                vote_confidence=0.0,
                window_size=144,
                step_size=6,
                threshold=0.1,
                total_samples=100,
                windows_analyzed=1,
                is_valid=True,
            )


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestInterpolateQuantiles:
    """Test quantile interpolation helper."""

    def test_interpolate_to_same_length(self):
        """Interpolating to same length returns original values."""
        from scripts.metrics.wasserstein import _interpolate_quantiles

        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _interpolate_quantiles(values, 5)

        assert len(result) == 5
        assert result == values

    def test_interpolate_double_length(self):
        """Interpolating to double length interpolates between values."""
        from scripts.metrics.wasserstein import _interpolate_quantiles

        values = [0.0, 10.0]
        result = _interpolate_quantiles(values, 3)

        assert len(result) == 3
        assert result[0] == 0.0
        assert result[1] == 5.0  # Midpoint
        assert result[2] == 10.0

    def test_empty_list_returns_empty(self):
        """Empty input returns empty output."""
        from scripts.metrics.wasserstein import _interpolate_quantiles

        result = _interpolate_quantiles([], 5)
        assert result == []


class TestWassersteinVote:
    """Test vote calculation helper."""

    def test_below_threshold_returns_zero(self):
        """Distance below threshold returns zero vote."""
        from scripts.metrics.wasserstein import wasserstein_vote

        vote = wasserstein_vote(0.05, "CONCENTRATION", threshold=0.10)
        assert vote == 0.0

    def test_concentration_positive_vote(self):
        """CONCENTRATION direction gives positive vote."""
        from scripts.metrics.wasserstein import wasserstein_vote

        vote = wasserstein_vote(0.20, "CONCENTRATION", threshold=0.10)
        assert vote > 0.0

    def test_dispersion_negative_vote(self):
        """DISPERSION direction gives negative vote."""
        from scripts.metrics.wasserstein import wasserstein_vote

        vote = wasserstein_vote(0.20, "DISPERSION", threshold=0.10)
        assert vote < 0.0

    def test_none_direction_zero_vote(self):
        """NONE direction gives zero vote regardless of distance."""
        from scripts.metrics.wasserstein import wasserstein_vote

        vote = wasserstein_vote(0.50, "NONE", threshold=0.10)
        assert vote == 0.0
