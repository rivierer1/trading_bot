document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    let priceChart = null;

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

    // Update positions table
    function updatePositions(positions) {
        const tbody = document.getElementById('positions-body');
        tbody.innerHTML = '';
        
        positions.forEach(position => {
            const pl = position.currentPrice - position.entryPrice;
            const plPercent = (pl / position.entryPrice) * 100;
            
            const row = `
                <tr>
                    <td>${position.symbol}</td>
                    <td>${position.quantity}</td>
                    <td>$${position.entryPrice.toFixed(2)}</td>
                    <td>$${position.currentPrice.toFixed(2)}</td>
                    <td class="${pl >= 0 ? 'positive' : 'negative'}">
                        $${pl.toFixed(2)} (${plPercent.toFixed(2)}%)
                    </td>
                </tr>
            `;
            tbody.insertAdjacentHTML('beforeend', row);
        });
    }

    // Update trades table
    function updateTrades(trades) {
        const tbody = document.getElementById('trades-body');
        tbody.innerHTML = '';
        
        trades.forEach(trade => {
            const row = `
                <tr>
                    <td>${new Date(trade.time).toLocaleString()}</td>
                    <td>${trade.symbol}</td>
                    <td class="${trade.action === 'BUY' ? 'positive' : 'negative'}">${trade.action}</td>
                    <td>${trade.quantity}</td>
                    <td>$${trade.price.toFixed(2)}</td>
                    <td>${trade.sentimentScore.toFixed(2)}</td>
                </tr>
            `;
            tbody.insertAdjacentHTML('beforeend', row);
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

    // Socket event handlers
    socket.on('connect', () => {
        document.getElementById('status-indicator').classList.add('active');
        document.getElementById('bot-status').textContent = 'Connected';
    });

    socket.on('disconnect', () => {
        document.getElementById('status-indicator').classList.remove('active');
        document.getElementById('bot-status').textContent = 'Disconnected';
    });

    socket.on('price_update', data => {
        if (priceChart) {
            priceChart.data.labels.push(new Date().toLocaleTimeString());
            priceChart.data.datasets[0].data.push(data.price);
            
            if (priceChart.data.labels.length > 50) {
                priceChart.data.labels.shift();
                priceChart.data.datasets[0].data.shift();
            }
            
            priceChart.update();
        }
    });

    socket.on('positions_update', updatePositions);
    socket.on('trades_update', updateTrades);
    socket.on('sentiment_update', updateSentiment);

    // Button event handlers
    document.getElementById('start-bot').addEventListener('click', () => {
        socket.emit('start_bot');
    });

    document.getElementById('stop-bot').addEventListener('click', () => {
        socket.emit('stop_bot');
    });

    // Initialize chart on load
    initializePriceChart();
});
