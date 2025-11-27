/**
 * UTXOracle Transaction Feed Component
 * Displays real-time whale transactions in a scrollable feed
 *
 * Tasks Implemented:
 * - T052: Transaction feed table component
 * - T053: Display transaction fields (time, amount, direction, urgency, fee rate)
 * - T054: Ring buffer (max 50 transactions)
 * - T055: Auto-scroll with pause on hover
 *
 * Features:
 * - Circular buffer (FIFO, max 50 transactions)
 * - Auto-scroll with pause on hover/focus
 * - Color-coded by direction (BUY/SELL/NEUTRAL)
 * - Urgency score highlighting
 * - Responsive table layout
 */

// ============================================
// Configuration
// ============================================

const FEED_CONFIG = {
    maxTransactions: 50,        // Ring buffer size
    autoScrollEnabled: true,    // Auto-scroll to newest
    pauseOnHover: true,         // Pause scroll on hover
    animationDuration: 300,     // Row fade-in animation (ms)
    urgencyThresholds: {
        high: 80,               // High urgency >= 80
        medium: 50,             // Medium urgency >= 50
        low: 0                  // Low urgency < 50
    }
};

// ============================================
// Ring Buffer
// ============================================

class RingBuffer {
    constructor(maxSize) {
        this.maxSize = maxSize;
        this.buffer = [];
    }

    push(item) {
        // Add to end
        this.buffer.push(item);

        // Remove from beginning if over limit
        if (this.buffer.length > this.maxSize) {
            this.buffer.shift();
        }
    }

    getAll() {
        return [...this.buffer];
    }

    clear() {
        this.buffer = [];
    }

    size() {
        return this.buffer.length;
    }

    isEmpty() {
        return this.buffer.length === 0;
    }
}

// ============================================
// Transaction Feed Component
// ============================================

class TransactionFeed {
    constructor(containerId, config = FEED_CONFIG) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Transaction feed container not found: ${containerId}`);
        }

        this.config = config;
        this.transactions = new RingBuffer(config.maxTransactions);

        // State
        this.isPaused = false;
        this.autoScrollEnabled = config.autoScrollEnabled;
        this.emptyState = null;

        // Initialize UI
        this.init();
    }

    // ========================================
    // Initialization
    // ========================================

    init() {
        // Save reference to empty state
        this.emptyState = this.container.querySelector('.feed-empty-state');

        // Create table structure
        this.createTable();

        // Setup hover/focus pause behavior
        if (this.config.pauseOnHover) {
            this.setupPauseBehavior();
        }
    }

    createTable() {
        const table = document.createElement('table');
        table.className = 'transaction-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th class="col-time">Time</th>
                    <th class="col-amount">Amount (BTC)</th>
                    <th class="col-usd">USD Value</th>
                    <th class="col-direction">Direction</th>
                    <th class="col-urgency">Urgency</th>
                    <th class="col-fee">Fee Rate</th>
                </tr>
            </thead>
            <tbody id="transaction-tbody">
                <!-- Rows will be added here -->
            </tbody>
        `;

        this.table = table;
        this.tbody = table.querySelector('#transaction-tbody');

        // Hide table initially (show empty state)
        table.classList.add('hidden');
    }

    setupPauseBehavior() {
        this.container.addEventListener('mouseenter', () => {
            this.pause();
        });

        this.container.addEventListener('mouseleave', () => {
            this.resume();
        });

        // Also pause when user is selecting text
        this.container.addEventListener('selectstart', () => {
            this.pause();
        });
    }

    // ========================================
    // Public API
    // ========================================

    addTransaction(tx) {
        // Add to ring buffer
        this.transactions.push(tx);

        // Show table if first transaction
        if (this.transactions.size() === 1) {
            this.showTable();
        }

        // Render new row
        this.renderTransaction(tx);

        // Auto-scroll to bottom if enabled and not paused
        if (this.autoScrollEnabled && !this.isPaused) {
            this.scrollToBottom();
        }
    }

    clear() {
        this.transactions.clear();
        this.tbody.innerHTML = '';
        this.hideTable();
    }

    pause() {
        this.isPaused = true;
        this.container.classList.add('paused');
    }

    resume() {
        this.isPaused = false;
        this.container.classList.remove('paused');

        // Scroll to bottom when resuming
        if (this.autoScrollEnabled) {
            this.scrollToBottom();
        }
    }

    toggleAutoScroll() {
        this.autoScrollEnabled = !this.autoScrollEnabled;
    }

    getTransactions() {
        return this.transactions.getAll();
    }

    // ========================================
    // Rendering
    // ========================================

    renderTransaction(tx) {
        const row = this.createTransactionRow(tx);

        // Add row to table
        this.tbody.appendChild(row);

        // Trigger fade-in animation
        setTimeout(() => {
            row.classList.add('visible');
        }, 10);

        // Remove oldest row if over limit
        if (this.tbody.children.length > this.config.maxTransactions) {
            const firstRow = this.tbody.firstChild;
            firstRow.classList.add('fade-out');

            setTimeout(() => {
                if (firstRow.parentNode) {
                    firstRow.remove();
                }
            }, this.config.animationDuration);
        }
    }

    createTransactionRow(tx) {
        const row = document.createElement('tr');
        row.className = `tx-row tx-${tx.direction.toLowerCase()}`;
        row.dataset.txId = tx.transaction_id;

        // Format time
        const time = this.formatTime(tx.timestamp);

        // Format amounts
        const btcAmount = this.formatBTC(tx.amount_btc);
        const usdAmount = this.formatUSD(tx.amount_usd);

        // Urgency class
        const urgencyClass = this.getUrgencyClass(tx.urgency_score);

        // Fee rate
        const feeRate = this.formatFeeRate(tx.fee_rate);

        row.innerHTML = `
            <td class="col-time">${time}</td>
            <td class="col-amount">${btcAmount}</td>
            <td class="col-usd">${usdAmount}</td>
            <td class="col-direction">
                <span class="direction-badge direction-${tx.direction.toLowerCase()}">
                    ${this.getDirectionSymbol(tx.direction)} ${tx.direction}
                </span>
            </td>
            <td class="col-urgency">
                <span class="urgency-badge urgency-${urgencyClass}">
                    ${tx.urgency_score}
                </span>
            </td>
            <td class="col-fee">${feeRate}</td>
        `;

        // Add click handler for details modal (future: T056)
        row.addEventListener('click', () => {
            this.onRowClick(tx);
        });

        return row;
    }

    // ========================================
    // Formatting Utilities
    // ========================================

    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    formatBTC(btc) {
        return parseFloat(btc).toFixed(2);
    }

    formatUSD(usd) {
        if (usd >= 1e9) {
            return '$' + (usd / 1e9).toFixed(2) + 'B';
        } else if (usd >= 1e6) {
            return '$' + (usd / 1e6).toFixed(2) + 'M';
        } else if (usd >= 1e3) {
            return '$' + (usd / 1e3).toFixed(2) + 'K';
        } else {
            return '$' + usd.toFixed(2);
        }
    }

    formatFeeRate(feeRate) {
        return parseFloat(feeRate).toFixed(1) + ' sat/vB';
    }

    getDirectionSymbol(direction) {
        switch (direction) {
            case 'BUY':
            case 'ACCUMULATION':
                return '↑';
            case 'SELL':
            case 'DISTRIBUTION':
                return '↓';
            default:
                return '→';
        }
    }

    getUrgencyClass(score) {
        const { high, medium } = this.config.urgencyThresholds;

        if (score >= high) return 'high';
        if (score >= medium) return 'medium';
        return 'low';
    }

    // ========================================
    // UI State Management
    // ========================================

    showTable() {
        if (this.emptyState) {
            this.emptyState.classList.add('hidden');
        }

        if (!this.table.parentNode) {
            this.container.appendChild(this.table);
        }

        this.table.classList.remove('hidden');
    }

    hideTable() {
        this.table.classList.add('hidden');

        if (this.emptyState) {
            this.emptyState.classList.remove('hidden');
        }
    }

    scrollToBottom() {
        // Smooth scroll to bottom
        this.container.scrollTo({
            top: this.container.scrollHeight,
            behavior: 'smooth'
        });
    }

    // ========================================
    // Event Handlers
    // ========================================

    onRowClick(tx) {
        // Emit event for modal display (T056)
        const event = new CustomEvent('transaction-selected', {
            detail: tx
        });
        this.container.dispatchEvent(event);
    }

    // ========================================
    // Export Functionality (T059)
    // ========================================

    exportToCSV() {
        const transactions = this.transactions.getAll();

        if (transactions.length === 0) {
            console.warn('No transactions to export');
            return null;
        }

        // CSV header
        const headers = [
            'Timestamp',
            'Transaction ID',
            'Amount BTC',
            'Amount USD',
            'Direction',
            'Urgency Score',
            'Fee Rate (sat/vB)',
            'Block Height',
            'Is Mempool'
        ];

        // CSV rows
        const rows = transactions.map(tx => [
            tx.timestamp,
            tx.transaction_id,
            tx.amount_btc,
            tx.amount_usd,
            tx.direction,
            tx.urgency_score,
            tx.fee_rate,
            tx.block_height || 'N/A',
            tx.is_mempool ? 'Yes' : 'No'
        ]);

        // Combine headers and rows
        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.join(','))
        ].join('\n');

        return csvContent;
    }

    downloadCSV() {
        const csv = this.exportToCSV();

        if (!csv) {
            return;
        }

        // Create blob
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });

        // Create download link
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);

        link.setAttribute('href', url);
        link.setAttribute('download', `whale_transactions_${Date.now()}.csv`);
        link.style.visibility = 'hidden';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        URL.revokeObjectURL(url);
    }
}

// ============================================
// Export
// ============================================

export { TransactionFeed, RingBuffer, FEED_CONFIG };
