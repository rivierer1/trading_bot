document.addEventListener('DOMContentLoaded', function() {
    // Initialize Socket.IO with debugging
    const socket = io({
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5
    });

    // Connect to Socket.IO server
    // const socket = io();

    socket.on('connect', () => {
        console.log('Connected to server');
        document.getElementById('status-indicator')?.classList.add('active');
        document.getElementById('bot-status-text').textContent = 'Connected';
    });

    socket.on('connect_error', (error) => {
        console.error('Connection error:', error);
        document.getElementById('status-indicator')?.classList.remove('active');
        document.getElementById('bot-status-text').textContent = 'Disconnected';
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        document.getElementById('status-indicator')?.classList.remove('active');
        document.getElementById('bot-status-text').textContent = 'Disconnected';
    });

    // Listen for portfolio updates
    socket.on('portfolio_update', function(data) {
        console.log('Received portfolio update:', data);
        updatePortfolioSummary(data);
        if (data.positions) {
            updatePortfolioCharts(data.positions);
        }
    });

    // Listen for positions updates
    socket.on('positions_update', function(data) {
        console.log('Received positions update:', data);
        updatePositionsTable(data);
    });

    // Listen for trades updates
    socket.on('trades_update', function(data) {
        console.log('Received trades update:', data);
        updateTradesTable(data);
    });

    function updatePortfolioSummary(data) {
        const summaryDiv = document.getElementById('portfolio-summary');
        if (!summaryDiv) return;

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
        const tbody = document.getElementById('positions-table-body');
        if (!tbody) return;

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
        const tbody = document.getElementById('trades-table-body');
        if (!tbody) return;

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
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(value);
    }

    function formatPercent(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }

    function formatDateTime(timestamp) {
        return new Date(timestamp).toLocaleString();
    }

    function updatePortfolioCharts(positions) {
        // Create treemap chart
        const treemapData = [{
            type: "treemap",
            labels: positions.map(p => p.symbol),
            parents: positions.map(() => "Portfolio"),
            values: positions.map(p => p.market_value),
            textinfo: "label+value+percent parent",
            marker: {
                colors: positions.map(p => p.unrealized_pl >= 0 ? '#28a745' : '#dc3545')
            }
        }];

        Plotly.newPlot('treemap-chart', treemapData);

        // Create allocation pie chart
        const pieData = [{
            type: "pie",
            labels: positions.map(p => p.symbol),
            values: positions.map(p => p.market_value),
            textinfo: "label+percent",
            hole: 0.4
        }];

        Plotly.newPlot('allocation-chart', pieData);
    }

    let priceChart = null;
    let marketDataInterval = null;
    const REFRESH_INTERVAL = 30000; // 30 seconds

    // Initialize price chart
    function initializePriceChart() {
        const ctx = document.getElementById('price-chart').getContext('2d');
        priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Price',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });
    }

    // Update sentiment display
    function updateSentiment(sentiment) {
        const container = document.querySelector('.tweets-container');
        container.innerHTML = '';
        
        sentiment.tweets.forEach(tweet => {
            const tweetElement = `
                <div class="tweet-item">
                    <p>${tweet.text}</p>
                    <small class="text-muted">${new Date(tweet.created_at).toLocaleString()}</small>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', tweetElement);
        });
    }

    // Test sentiment function
    async function testSentiment(symbol) {
        try {
            const response = await fetch(`/api/test_sentiment?symbol=${encodeURIComponent(symbol)}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error testing sentiment:', error);
            throw error;
        }
    }

    // Add test sentiment button handler
    document.getElementById('test-sentiment-btn')?.addEventListener('click', async () => {
        const symbolInput = document.getElementById('symbol-input');
        const resultDiv = document.getElementById('sentiment-result');
        
        if (!symbolInput || !resultDiv) {
            console.error('Required DOM elements not found');
            return;
        }

        const symbol = symbolInput.value.trim().toUpperCase();
        if (!symbol) {
            alert('Please enter a valid symbol');
            return;
        }

        try {
            resultDiv.innerHTML = 'Loading...';
            const data = await testSentiment(symbol);
            
            // Display results
            let html = `
                <h4>Results for ${data.symbol}</h4>
                <p>Sentiment Score: ${data.sentiment_score.toFixed(2)}</p>
                <p>Analyzed ${data.tweet_count} tweets</p>
                <div class="tweets-list">
                    ${data.tweets.map(tweet => `
                        <div class="tweet">
                            <p>${tweet}</p>
                        </div>
                    `).join('')}
                </div>
            `;
            resultDiv.innerHTML = html;
        } catch (error) {
            resultDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
        }
    });

    // Market Data Management
    async function updateMarketData() {
        try {
            // Check market status
            const statusResponse = await fetch('/api/market/status');
            const statusData = await statusResponse.json();
            
            if (!statusData.is_open) {
                document.getElementById('market-status').innerHTML = '<span class="badge bg-danger">Market Closed</span>';
                return;
            }
            
            document.getElementById('market-status').innerHTML = '<span class="badge bg-success">Market Open</span>';
            
            // Get market snapshot
            const snapshotResponse = await fetch('/api/market/snapshot?symbols=SPY,QQQ,DIA,AAPL,MSFT,GOOGL');
            const snapshotData = await snapshotResponse.json();
            
            // Update market overview
            const marketOverview = document.getElementById('market-overview');
            marketOverview.innerHTML = '';
            
            for (const [symbol, data] of Object.entries(snapshotData)) {
                const changeClass = data.change >= 0 ? 'text-success' : 'text-danger';
                const changeArrow = data.change >= 0 ? '▲' : '▼';
                
                marketOverview.innerHTML += `
                    <div class="col-md-4 mb-3">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">${symbol}</h5>
                                <p class="card-text">
                                    Price: $${data.price.toFixed(2)}<br>
                                    Change: <span class="${changeClass}">${changeArrow} ${Math.abs(data.change).toFixed(2)}%</span><br>
                                    Volume: ${data.volume.toLocaleString()}<br>
                                    Time: ${new Date(data.time).toLocaleTimeString()}
                                </p>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // Get market breadth
            const breadthResponse = await fetch('/api/market/breadth');
            const breadthData = await breadthResponse.json();
            
            // Update market breadth
            const breadthDiv = document.getElementById('market-breadth');
            breadthDiv.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Market Breadth</h5>
                        <p class="card-text">
                            Advancing: ${breadthData.advancing}<br>
                            Declining: ${breadthData.declining}<br>
                        </p>
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Top Gainers</h6>
                                <ul class="list-unstyled">
                                    ${breadthData.top_gainers.map(stock => 
                                        `<li>${stock.symbol}: +${stock.change.toFixed(2)}%</li>`
                                    ).join('')}
                                </ul>
                            </div>
                            <div class="col-md-6">
                                <h6>Top Losers</h6>
                                <ul class="list-unstyled">
                                    ${breadthData.top_losers.map(stock => 
                                        `<li>${stock.symbol}: ${stock.change.toFixed(2)}%</li>`
                                    ).join('')}
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
        } catch (error) {
            console.error('Error updating market data:', error);
        }
    }

    // Start market data updates
    function startMarketDataUpdates() {
        updateMarketData(); // Initial update
        marketDataInterval = setInterval(updateMarketData, REFRESH_INTERVAL);
    }

    // Stop market data updates
    function stopMarketDataUpdates() {
        if (marketDataInterval) {
            clearInterval(marketDataInterval);
            marketDataInterval = null;
        }
    }

    // Technical Analysis
    async function updateTechnicalData(symbol) {
        try {
            const [technicalResponse, vwapResponse] = await Promise.all([
                fetch(`/api/market/technical/${symbol}`),
                fetch(`/api/market/vwap/${symbol}`)
            ]);
            
            const technicalData = await technicalResponse.json();
            const vwapData = await vwapResponse.json();
            
            const technicalDiv = document.getElementById('technical-analysis');
            technicalDiv.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Technical Analysis - ${symbol}</h5>
                        <p class="card-text">
                            Current Price: $${technicalData.current_price.toFixed(2)}<br>
                            SMA (5): $${technicalData.sma_5.toFixed(2)}<br>
                            SMA (20): $${technicalData.sma_20.toFixed(2)}<br>
                            RSI: ${technicalData.rsi.toFixed(2)}<br>
                            VWAP: $${vwapData.vwap.toFixed(2)}<br>
                            Volume: ${technicalData.volume.toLocaleString()}
                        </p>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Error updating technical data:', error);
        }
    }

    // Portfolio Functions
    function formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(value);
    }

    function formatPercentage(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value / 100);
    }

    function updatePortfolioSummaryFromData(data) {
        try {
            console.log('Updating portfolio summary with data:', data);
            if (!data) {
                throw new Error('No portfolio data received');
            }

            // Check if the update was successful
            if (!data.last_update_successful) {
                throw new Error(data.error || 'Failed to update portfolio data');
            }

            // Create status indicator
            const statusIndicator = `
                <div class="col-12 mb-3">
                    <div class="alert alert-success alert-dismissible fade show" role="alert">
                        Last updated: ${new Date(data.timestamp).toLocaleString()}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                </div>`;

            const summaryHtml = `
                ${statusIndicator}
                <div class="col-md-3 mb-3">
                    <div class="metric">
                        <h6>Portfolio Value</h6>
                        <h4>${formatCurrency(data.portfolio_value)}</h4>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="metric">
                        <h6>Total P/L</h6>
                        <h4 class="${data.total_pl >= 0 ? 'text-success' : 'text-danger'}">
                            ${formatCurrency(data.total_pl)}
                        </h4>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="metric">
                        <h6>Daily P/L</h6>
                        <h4 class="${data.daily_pl >= 0 ? 'text-success' : 'text-danger'}">
                            ${formatCurrency(data.daily_pl)}
                            <small>(${formatPercentage(data.daily_pl_percent)})</small>
                        </h4>
                    </div>
                </div>
                <div class="col-md-3 mb-3">
                    <div class="metric">
                        <h6>Cash Balance</h6>
                        <h4>${formatCurrency(data.cash)}</h4>
                        <small>Buying Power: ${formatCurrency(data.buying_power)}</small>
                    </div>
                </div>`;

            const summaryElement = document.getElementById('portfolio-summary');
            if (summaryElement) {
                summaryElement.innerHTML = summaryHtml;
                console.log('Portfolio summary updated successfully');
            } else {
                console.error('Portfolio summary element not found');
            }
        } catch (error) {
            console.error('Error updating portfolio summary:', error);
            const errorHtml = `
                <div class="col-12">
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        <strong>Update Failed:</strong> ${error.message}
                        <br>
                        <small>Last attempt: ${new Date().toLocaleString()}</small>
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                </div>`;

            const summaryElement = document.getElementById('portfolio-summary');
            if (summaryElement) {
                // Preserve existing data if available
                if (!summaryElement.querySelector('.alert-danger')) {
                    summaryElement.insertAdjacentHTML('afterbegin', errorHtml);
                } else {
                    const existingError = summaryElement.querySelector('.alert-danger');
                    existingError.outerHTML = errorHtml;
                }
            }
        }
    }

    function updatePositionsFromData(positions) {
        try {
            console.log('Updating positions with data:', positions);
            if (!Array.isArray(positions)) {
                throw new Error('Invalid positions data received');
            }

            const tableBody = document.getElementById('positions-table-body');
            if (!tableBody) {
                throw new Error('Positions table body not found');
            }

            // Sort positions by market value
            positions.sort((a, b) => b.market_value - a.market_value);

            tableBody.innerHTML = positions.map(pos => `
                <tr>
                    <td>${pos.symbol}</td>
                    <td>${pos.qty}</td>
                    <td>${formatCurrency(pos.avg_entry_price)}</td>
                    <td>${formatCurrency(pos.current_price)}</td>
                    <td>${formatCurrency(pos.market_value)}</td>
                    <td class="${pos.unrealized_pl >= 0 ? 'text-success' : 'text-danger'}">
                        ${formatCurrency(pos.unrealized_pl)}
                        <small>(${formatPercentage(pos.unrealized_plpc)})</small>
                    </td>
                </tr>
            `).join('');

            // Update positions count
            const positionsCount = document.getElementById('positions-count');
            if (positionsCount) {
                positionsCount.textContent = positions.length;
            }

            console.log('Positions table updated successfully');
        } catch (error) {
            console.error('Error updating positions table:', error);
            const tableBody = document.getElementById('positions-table-body');
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center text-danger">
                            Error updating positions: ${error.message}
                        </td>
                    </tr>`;
            }
        }
    }

    function updateTradesFromData(trades) {
        try {
            console.log('Updating trades with data:', trades);
            if (!Array.isArray(trades)) {
                throw new Error('Invalid trades data received');
            }

            const tableBody = document.getElementById('trades-table-body');
            if (!tableBody) {
                throw new Error('Trades table body not found');
            }

            if (trades.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center">
                            No recent trades available
                        </td>
                    </tr>`;
                return;
            }

            tableBody.innerHTML = trades.map(trade => `
                <tr>
                    <td>${new Date(trade.timestamp).toLocaleString()}</td>
                    <td>${trade.symbol}</td>
                    <td class="${trade.side.toLowerCase() === 'buy' ? 'text-success' : 'text-danger'}">
                        ${trade.side}
                    </td>
                    <td>${trade.qty}</td>
                    <td>${formatCurrency(trade.price)}</td>
                    <td>${formatCurrency(trade.qty * trade.price)}</td>
                </tr>
            `).join('');

            console.log('Trades table updated successfully');
        } catch (error) {
            console.error('Error updating trades table:', error);
            const tableBody = document.getElementById('trades-table-body');
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="text-center text-danger">
                            Error updating trades: ${error.message}
                        </td>
                    </tr>`;
            }
        }
    }

    // Initialize portfolio updates
    console.log('Initializing portfolio updates...');
    // Initial data fetch
    fetch('/api/portfolio/summary')
        .then(response => response.json())
        .then(data => {
            console.log('Initial portfolio data received:', data);
            updatePortfolioSummaryFromData(data);
        })
        .catch(error => console.error('Error fetching initial portfolio data:', error));

    fetch('/api/portfolio/positions')
        .then(response => response.json())
        .then(data => {
            console.log('Initial positions data received:', data);
            updatePositionsFromData(data);
        })
        .catch(error => console.error('Error fetching initial positions data:', error));

    fetch('/api/trades/recent')
        .then(response => response.json())
        .then(data => {
            console.log('Initial trades data received:', data);
            updateTradesFromData(data);
        })
        .catch(error => console.error('Error fetching initial trades data:', error));

    // Add event listeners for bot control buttons
    document.getElementById('start-bot')?.addEventListener('click', () => {
        console.log('Start bot clicked');
        socket.emit('start_bot');
    });

    document.getElementById('stop-bot')?.addEventListener('click', () => {
        console.log('Stop bot clicked');
        socket.emit('stop_bot');
    });

    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        console.log('Page unloading, cleaning up...');
        socket.disconnect();
    });

    // Initialize chart on load
    initializePriceChart();

    // Add symbol search functionality
    const symbolForm = document.getElementById('symbol-form');
    symbolForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const symbol = document.getElementById('symbol-input').value.toUpperCase();
        updateTechnicalData(symbol);
    });

    // Initialize market data updates
    startMarketDataUpdates();
});
