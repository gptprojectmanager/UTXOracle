/**
 * UTXOracle Whale Detection Dashboard
 * Main JavaScript module for real-time whale activity monitoring
 *
 * Tasks Implemented:
 * - T041: Net flow display component (BTC + USD values)
 * - T042: Direction indicator (accumulation/distribution/neutral)
 * - T043: API endpoint connection
 * - T044: 5-second polling mechanism
 * - T045: Loading states and error handling
 * - T046: Number formatting (K, M, B suffixes)
 */

// ============================================
// Configuration
// ============================================

const CONFIG = {
    apiEndpoint: '/api/whale/latest',
    pollInterval: 5000, // 5 seconds
    maxRetries: 3,
    retryDelay: 2000,
};

// ============================================
// Utility Functions
// ============================================

/**
 * Format large numbers with K, M, B suffixes
 * @param {number} num - Number to format
 * @param {number} decimals - Decimal places
 * @returns {string} Formatted number
 */
function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return '0';

    const absNum = Math.abs(num);

    if (absNum >= 1e9) {
        return (num / 1e9).toFixed(decimals) + 'B';
    } else if (absNum >= 1e6) {
        return (num / 1e6).toFixed(decimals) + 'M';
    } else if (absNum >= 1e3) {
        return (num / 1e3).toFixed(decimals) + 'K';
    } else {
        return num.toFixed(decimals);
    }
}

/**
 * Format BTC amount with proper precision
 * @param {number} btc - BTC amount
 * @returns {string} Formatted BTC string
 */
function formatBTC(btc) {
    if (btc === null || btc === undefined || isNaN(btc)) return '0.00';
    return parseFloat(btc).toFixed(2);
}

/**
 * Format USD amount with commas
 * @param {number} usd - USD amount
 * @returns {string} Formatted USD string
 */
function formatUSD(usd) {
    if (usd === null || usd === undefined || isNaN(usd)) return '$0';
    return '$' + formatNumber(usd, 0);
}

/**
 * Get human-readable timestamp
 * @returns {string} Formatted timestamp
 */
function getTimestamp() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// ============================================
// Dashboard State
// ============================================

class DashboardState {
    constructor() {
        this.connected = false;
        this.loading = true;
        this.error = null;
        this.lastUpdate = null;
        this.retryCount = 0;
        this.pollTimer = null;

        this.netFlowData = {
            btc: 0,
            usd: 0,
            direction: 'NEUTRAL',
            timestamp: null
        };
    }

    updateNetFlow(data) {
        this.netFlowData = {
            btc: data.whale_net_flow || 0,
            usd: (data.whale_net_flow || 0) * (data.btc_price || 40000), // Approximate
            direction: data.whale_direction || 'NEUTRAL',
            timestamp: new Date()
        };
        this.lastUpdate = new Date();
        this.error = null;
        this.retryCount = 0;
    }

    markError(error) {
        this.error = error;
        this.retryCount++;
    }

    reset() {
        this.error = null;
        this.retryCount = 0;
    }
}

// ============================================
// UI Controller
// ============================================

class UIController {
    constructor() {
        this.elements = {
            // Status bar
            connectionStatus: document.getElementById('connection-status'),
            lastUpdate: document.getElementById('last-update'),

            // Net flow display
            netFlowLoading: document.getElementById('net-flow-loading'),
            netFlowContent: document.getElementById('net-flow-content'),
            netFlowError: document.getElementById('net-flow-error'),

            valueBTC: document.getElementById('value-btc'),
            valueUSD: document.getElementById('value-usd'),

            // Direction indicator
            directionIndicator: document.getElementById('direction-indicator'),
            directionArrow: document.getElementById('direction-arrow'),
            directionLabel: document.getElementById('direction-label'),
            directionDescription: document.getElementById('direction-description'),

            // Controls
            retryButton: document.getElementById('retry-button'),
        };
    }

    showLoading() {
        this.elements.netFlowLoading.classList.remove('hidden');
        this.elements.netFlowContent.classList.add('hidden');
        this.elements.netFlowError.classList.add('hidden');
    }

    showContent() {
        this.elements.netFlowLoading.classList.add('hidden');
        this.elements.netFlowContent.classList.remove('hidden');
        this.elements.netFlowError.classList.add('hidden');
    }

    showError(message) {
        this.elements.netFlowLoading.classList.add('hidden');
        this.elements.netFlowContent.classList.add('hidden');
        this.elements.netFlowError.classList.remove('hidden');

        const errorMsg = this.elements.netFlowError.querySelector('.error-message');
        if (errorMsg) {
            errorMsg.textContent = `⚠️ ${message}`;
        }
    }

    updateConnectionStatus(connected, message = '') {
        const statusEl = this.elements.connectionStatus;

        if (connected) {
            statusEl.className = 'status-indicator connected';
            statusEl.querySelector('.status-text').textContent = 'Connected';
        } else {
            statusEl.className = 'status-indicator disconnected';
            statusEl.querySelector('.status-text').textContent = message || 'Disconnected';
        }
    }

    updateLastUpdate(timestamp) {
        if (timestamp) {
            this.elements.lastUpdate.textContent = `Last update: ${getTimestamp()}`;
        } else {
            this.elements.lastUpdate.textContent = 'No data yet';
        }
    }

    updateNetFlowDisplay(data) {
        // Update BTC value with appropriate color
        const btcValue = data.btc;
        const btcFormatted = formatBTC(Math.abs(btcValue));
        const btcSign = btcValue >= 0 ? '+' : '-';

        this.elements.valueBTC.textContent = `${btcSign}${btcFormatted} BTC`;
        this.elements.valueBTC.style.color = this.getDirectionColor(data.direction);

        // Update USD value
        this.elements.valueUSD.textContent = formatUSD(Math.abs(data.usd));
    }

    updateDirectionIndicator(direction) {
        const indicator = this.elements.directionIndicator;
        const arrow = this.elements.directionArrow.querySelector('.arrow-symbol');
        const label = this.elements.directionLabel;
        const description = this.elements.directionDescription;

        // Remove all direction classes
        indicator.classList.remove('accumulation', 'distribution', 'neutral');

        // Add appropriate class and update content
        switch (direction) {
            case 'BUY':
            case 'ACCUMULATION':
                indicator.classList.add('accumulation');
                arrow.textContent = '↑';
                label.textContent = 'ACCUMULATION';
                description.textContent = 'Whales are buying Bitcoin';
                break;

            case 'SELL':
            case 'DISTRIBUTION':
                indicator.classList.add('distribution');
                arrow.textContent = '↓';
                label.textContent = 'DISTRIBUTION';
                description.textContent = 'Whales are selling Bitcoin';
                break;

            case 'NEUTRAL':
            default:
                indicator.classList.add('neutral');
                arrow.textContent = '→';
                label.textContent = 'NEUTRAL';
                description.textContent = 'No significant whale activity';
                break;
        }
    }

    getDirectionColor(direction) {
        switch (direction) {
            case 'BUY':
            case 'ACCUMULATION':
                return 'var(--color-accent-buy)';
            case 'SELL':
            case 'DISTRIBUTION':
                return 'var(--color-accent-sell)';
            case 'NEUTRAL':
            default:
                return 'var(--color-accent-neutral)';
        }
    }
}

// ============================================
// API Client
// ============================================

class WhaleAPIClient {
    constructor(endpoint) {
        this.endpoint = endpoint;
    }

    async fetchLatest() {
        try {
            const response = await fetch(this.endpoint);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return { success: true, data };

        } catch (error) {
            console.error('API fetch error:', error);
            return { success: false, error: error.message };
        }
    }
}

// ============================================
// Main Dashboard Controller
// ============================================

class WhaleDashboard {
    constructor() {
        this.state = new DashboardState();
        this.ui = new UIController();
        this.api = new WhaleAPIClient(CONFIG.apiEndpoint);

        this.setupEventListeners();
        this.initialize();
    }

    setupEventListeners() {
        // Retry button
        this.ui.elements.retryButton.addEventListener('click', () => {
            this.state.reset();
            this.initialize();
        });

        // Handle page visibility changes (pause polling when hidden)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopPolling();
            } else {
                this.startPolling();
            }
        });
    }

    async initialize() {
        console.log('Initializing Whale Detection Dashboard...');

        this.ui.showLoading();
        this.ui.updateConnectionStatus(false, 'Connecting...');

        // Initial data fetch
        const result = await this.api.fetchLatest();

        if (result.success) {
            this.handleDataUpdate(result.data);
            this.startPolling();
        } else {
            this.handleError(result.error);
        }
    }

    handleDataUpdate(data) {
        this.state.updateNetFlow(data);
        this.state.connected = true;
        this.state.loading = false;

        this.ui.updateConnectionStatus(true);
        this.ui.updateLastUpdate(this.state.lastUpdate);
        this.ui.updateNetFlowDisplay(this.state.netFlowData);
        this.ui.updateDirectionIndicator(this.state.netFlowData.direction);
        this.ui.showContent();

        console.log('Data updated:', {
            netFlow: this.state.netFlowData.btc,
            direction: this.state.netFlowData.direction,
            timestamp: this.state.lastUpdate.toISOString()
        });
    }

    handleError(errorMessage) {
        this.state.markError(errorMessage);
        this.state.connected = false;

        this.ui.updateConnectionStatus(false, 'Connection failed');
        this.ui.showError(errorMessage || 'Unable to connect to API');

        console.error('Dashboard error:', errorMessage);

        // Retry logic
        if (this.state.retryCount < CONFIG.maxRetries) {
            console.log(`Retrying in ${CONFIG.retryDelay / 1000}s... (attempt ${this.state.retryCount}/${CONFIG.maxRetries})`);
            setTimeout(() => this.initialize(), CONFIG.retryDelay);
        }
    }

    startPolling() {
        if (this.state.pollTimer) {
            clearInterval(this.state.pollTimer);
        }

        console.log(`Starting polling (interval: ${CONFIG.pollInterval / 1000}s)`);

        this.state.pollTimer = setInterval(async () => {
            const result = await this.api.fetchLatest();

            if (result.success) {
                this.handleDataUpdate(result.data);
            } else {
                console.warn('Poll failed:', result.error);
                // Don't show error UI for intermittent failures, just log
                // Only show error if multiple consecutive failures occur
            }
        }, CONFIG.pollInterval);
    }

    stopPolling() {
        if (this.state.pollTimer) {
            console.log('Stopping polling');
            clearInterval(this.state.pollTimer);
            this.state.pollTimer = null;
        }
    }
}

// ============================================
// Initialize Dashboard
// ============================================

// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}

function initDashboard() {
    console.log('DOM ready, starting dashboard...');

    // Create global dashboard instance
    window.whaleDashboard = new WhaleDashboard();

    // Handle cleanup on page unload
    window.addEventListener('beforeunload', () => {
        if (window.whaleDashboard) {
            window.whaleDashboard.stopPolling();
        }
    });
}

// Export for testing
export { WhaleDashboard, formatNumber, formatBTC, formatUSD };
