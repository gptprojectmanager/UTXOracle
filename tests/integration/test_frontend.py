"""
Frontend Integration Tests

Tests for Canvas rendering and browser-side visualization.

Note: Some tests require a browser environment (Playwright/Selenium) and are marked
with @pytest.mark.browser. These can be run separately using:
    pytest tests/integration/test_frontend.py -m browser

For full frontend validation, use browser MCP tools (ccbrowser, ccfullbrowser).
"""

from pathlib import Path


# =============================================================================
# T085: Stats Panel Rendering Test (User Story 4)
# =============================================================================


def test_stats_panel_rendering():
    """
    Test that HTML contains stats panel and JavaScript updates it.

    Requirements (User Story 4):
    - HTML contains stats display area
    - JavaScript receives stats from WebSocket message
    - Stats displayed: "Received: X | Filtered: Y | Active: Z | Uptime: Xh Ym"
    - Uptime formatted as hours/minutes (not raw seconds)
    - Connection status indicator present

    This is a STRUCTURAL test (checks files and elements exist).
    Visual rendering requires browser environment - see manual testing notes.

    Task: T085 [US4]
    """
    # Assert: HTML file exists
    html_path = Path("live/frontend/index.html")
    assert html_path.exists(), f"Frontend HTML not found: {html_path}"

    # Assert: JavaScript module exists
    js_path = Path("live/frontend/mempool-viz.js")
    assert js_path.exists(), f"Visualization JS not found: {js_path}"

    # Assert: HTML contains stats display area
    html_content = html_path.read_text()

    # Check for stats panel in HTML (any of these patterns)
    has_stats_section = any(
        [
            'id="stats"' in html_content,
            "id='stats'" in html_content,
            'class="stats"' in html_content,
            "class='stats'" in html_content,
            '<div class="stats-panel">' in html_content,
            '<section class="stats">' in html_content,
        ]
    )
    assert has_stats_section, (
        "HTML should contain stats display area (id='stats' or class='stats')"
    )

    # Assert: JavaScript handles stats updates
    js_content = js_path.read_text()

    # Check for stats-related code (any of these patterns)
    has_stats_handling = any(
        [
            "total_received" in js_content,
            "totalReceived" in js_content,
            "active_tx_count" in js_content,
            "activeTxCount" in js_content,
            "uptime" in js_content.lower(),
        ]
    )
    assert has_stats_handling, "JavaScript should handle stats from WebSocket message"

    # Assert: Uptime formatting exists (hours/minutes, not raw seconds)
    has_uptime_format = any(
        [
            "hours" in js_content.lower() or "minutes" in js_content.lower(),
            "formatUptime" in js_content,
            "format_uptime" in js_content,
            "/ 3600" in js_content,  # seconds to hours conversion
            "/ 60" in js_content,  # seconds/minutes to minutes conversion
        ]
    )
    assert has_uptime_format, "JavaScript should format uptime as hours/minutes"

    # Assert: Connection status indicator exists (from US1, should still be present)
    has_connection_status = any(
        [
            "connection" in js_content.lower() and "status" in js_content.lower(),
            "connected" in js_content.lower(),
            "disconnected" in js_content.lower(),
        ]
    )
    assert has_connection_status, "JavaScript should have connection status handling"


# =============================================================================
# T066: Canvas Rendering Test (User Story 2)
# =============================================================================


def test_scatter_plot_renders_transactions():
    """
    Test that Canvas scatter plot can render transaction history.

    Requirements (User Story 2):
    - HTML contains canvas element with correct ID
    - JavaScript module exists with scatter plot renderer
    - Canvas has correct dimensions (1000x660px per spec)
    - Renderer can process WebSocket message format
    - Points are rendered as orange circles
    - X-axis: time (horizontal), Y-axis: price (vertical)

    This is a STRUCTURAL test (checks files and structure exist).
    Visual rendering requires browser environment - see manual testing notes.

    Task: T066 [US2]
    """
    # Assert: HTML file exists
    html_path = Path("live/frontend/index.html")
    assert html_path.exists(), f"Frontend HTML not found: {html_path}"

    # Assert: JavaScript visualization module exists
    js_path = Path("live/frontend/mempool-viz.js")
    assert js_path.exists(), f"Visualization JS not found: {js_path}"

    # Assert: HTML contains canvas element
    html_content = html_path.read_text()
    assert "<canvas" in html_content, "HTML should contain canvas element"
    assert (
        'id="mempool-canvas"' in html_content or "id='mempool-canvas'" in html_content
    ), "Canvas should have id='mempool-canvas'"

    # Assert: Canvas dimensions specified (1000x660px per spec)
    assert "1000" in html_content and "660" in html_content, (
        "Canvas should have dimensions 1000x660px (per spec.md Visual Reference)"
    )

    # Assert: JavaScript file loaded in HTML
    assert "mempool-viz.js" in html_content, "HTML should load mempool-viz.js script"

    # Assert: JavaScript module structure (basic validation)
    js_content = js_path.read_text()

    # Assert: WebSocket connection code present in JS (not HTML)
    assert "WebSocket" in js_content or "new WebSocket" in js_content, (
        "JavaScript should contain WebSocket connection code"
    )

    # Check for required Canvas rendering functions/classes
    required_elements = [
        (
            "class MempoolVisualizer" in js_content
            or "function MempoolVisualizer" in js_content,
            "MempoolVisualizer class/function not found (required for Canvas scatter plot)",
        ),
        (
            "render" in js_content.lower() or "draw" in js_content.lower(),
            "No render/draw method found (required for Canvas scatter plot)",
        ),
        (
            "canvas" in js_content.lower() and "ctx" in js_content.lower(),
            "No Canvas context reference found (required for 2D rendering)",
        ),
    ]

    for condition, error_msg in required_elements:
        assert condition, error_msg


# =============================================================================
# T076: Low Confidence Warning Display Test (User Story 3)
# =============================================================================


def test_confidence_warning_display():
    """
    Test that HTML contains confidence warning element.

    Requirements (User Story 3):
    - Warning element exists in HTML
    - Warning text: "⚠ Low confidence - warming up"
    - CSS class for show/hide: confidence-warning

    Task: T076 [US3]
    """
    # Assert: HTML file exists
    html_path = Path("live/frontend/index.html")
    assert html_path.exists(), "Frontend HTML not found"

    html_content = html_path.read_text()

    # Assert: Warning element exists
    assert "confidence-warning" in html_content, "Missing confidence warning element"
    assert "Low confidence" in html_content, "Missing low confidence warning text"
    assert "warming up" in html_content, "Missing warming up text"

    # Assert: CSS file has warning styles
    css_path = Path("live/frontend/styles.css")
    assert css_path.exists(), "CSS file not found"

    css_content = css_path.read_text()

    assert ".confidence-warning" in css_content, (
        "Missing CSS class for confidence warning"
    )
    assert ".confidence-high" in css_content or "confidence-high" in css_content, (
        "Missing high confidence CSS"
    )
    assert ".confidence-medium" in css_content or "confidence-medium" in css_content, (
        "Missing medium confidence CSS"
    )
    assert ".confidence-low" in css_content or "confidence-low" in css_content, (
        "Missing low confidence CSS"
    )
