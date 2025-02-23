document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initialized');
    
    // Connect to Socket.IO server
    const socket = io();

    // Socket connection events
    socket.on('connect', () => {
        console.log('Socket.IO connected');
        document.getElementById('connection-status').textContent = 'Connected';
    });

    socket.on('disconnect', () => {
        console.log('Socket.IO disconnected');
        document.getElementById('connection-status').textContent = 'Disconnected';
    });

    // Listen for portfolio updates
    socket.on('portfolio_update', function(data) {
        console.log('Received portfolio update:', data);
        if (!data) {
            console.error('No portfolio data received');
            return;
        }
        updatePortfolioSummary(data);
    });

    // Listen for positions updates
    socket.on('positions_update', function(data) {
        console.log('Received positions update:', data);
        if (!data) {
            console.error('No positions data received');
            return;
        }
        updatePositionsTable(data);
    });

    // Listen for trades updates
    socket.on('trades_update', function(data) {
        console.log('Received trades update:', data);
        if (!data) {
            console.error('No trades data received');
            return;
        }
        updateTradesTable(data);
    });

    function updatePortfolioSummary(data) {
        console.log('Updating portfolio summary with:', data);
        const summaryDiv = document.getElementById('portfolio-summary');
        if (!summaryDiv) {
            console.error('Portfolio summary div not found');
            return;
        }

        const metrics = [
            { label: 'Portfolio Value', value: formatCurrency(data.portfolio_value) },
            { label: 'Cash', value: formatCurrency(data.cash) },
            { label: 'Buying Power', value: formatCurrency(data.buying_power) },
            { label: 'Total P/L', value: formatCurrency(data.total_pl), class: data.total_pl >= 0 ? 'text-success' : 'text-danger' },
            { label: 'Daily P/L', value: formatCurrency(data.daily_pl), class: data.daily_pl >= 0 ? 'text-success' : 'text-danger' },
            { label: 'Daily P/L %', value: formatPercent(data.daily_pl_percent), class: data.daily_pl_percent >= 0 ? 'text-success' : 'text-danger' }
        ];

        summaryDiv.innerHTML = metrics.map(metric => `
            <div class="col-md-4 col-lg-2 mb-3">
                <div class="card h-100">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">${metric.label}</h6>
                        <h5 class="card-title ${metric.class || ''}">${metric.value}</h5>
                    </div>
                </div>
            </div>
        `).join('');

        // Update positions count badge
        const positionsCountBadge = document.getElementById('positions-count');
        if (positionsCountBadge) {
            positionsCountBadge.textContent = data.positions_count || '0';
        }
    }

    function updatePositionsTable(positions) {
        console.log('Updating positions table with:', positions);
        const tbody = document.getElementById('positions-table-body');
        if (!tbody) {
            console.error('Positions table body not found');
            return;
        }

        if (!positions || positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No positions found</td></tr>';
            return;
        }

        tbody.innerHTML = positions.map(position => `
            <tr>
                <td>${position.symbol}</td>
                <td>${position.qty}</td>
                <td>${formatCurrency(position.avg_entry_price)}</td>
                <td>${formatCurrency(position.current_price)}</td>
                <td>${formatCurrency(position.market_value)}</td>
                <td class="${position.unrealized_pl >= 0 ? 'text-success' : 'text-danger'}">
                    ${formatCurrency(position.unrealized_pl)} (${formatPercent(position.unrealized_plpc)})
                </td>
            </tr>
        `).join('');
    }

    function updateTradesTable(trades) {
        console.log('Updating trades table with:', trades);
        const tbody = document.getElementById('trades-table-body');
        if (!tbody) {
            console.error('Trades table body not found');
            return;
        }

        if (!trades || trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No recent trades</td></tr>';
            return;
        }

        tbody.innerHTML = trades.map(trade => `
            <tr>
                <td>${formatDateTime(trade.timestamp)}</td>
                <td>${trade.symbol}</td>
                <td class="${trade.side === 'buy' ? 'text-success' : 'text-danger'}">${trade.side.toUpperCase()}</td>
                <td>${trade.qty}</td>
                <td>${formatCurrency(trade.price)}</td>
                <td>${formatCurrency(trade.qty * trade.price)}</td>
            </tr>
        `).join('');
    }

    // Utility functions
    function formatCurrency(value) {
        if (value === undefined || value === null) {
            console.warn('Attempting to format undefined/null currency value');
            return '$0.00';
        }
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(value);
    }

    function formatPercent(value) {
        if (value === undefined || value === null) {
            console.warn('Attempting to format undefined/null percentage value');
            return '0.00%';
        }
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }

    function formatDateTime(timestamp) {
        if (!timestamp) {
            console.warn('Attempting to format undefined/null timestamp');
            return 'N/A';
        }
        return new Date(timestamp).toLocaleString();
    }

    // Request initial data
    console.log('Requesting initial data...');
    socket.emit('request_initial_data');
});
