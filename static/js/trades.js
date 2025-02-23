document.addEventListener('DOMContentLoaded', function() {
    function formatCurrency(value) {
        if (value === null || value === undefined) return '-';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(value);
    }

    function formatPercentage(value) {
        if (value === null || value === undefined) return '-';
        return new Intl.NumberFormat('en-US', {
            style: 'percent',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value / 100);
    }

    function updateTrades() {
        fetch('/api/trades/recent')
            .then(response => response.json())
            .then(trades => {
                const tbody = document.getElementById('trades-body');
                tbody.innerHTML = '';
                
                trades.forEach(trade => {
                    const row = `
                        <tr>
                            <td>${trade.symbol}</td>
                            <td class="${trade.side === 'BUY' ? 'text-success' : 'text-danger'}">${trade.side}</td>
                            <td>${trade.quantity}</td>
                            <td>${formatCurrency(trade.price)}</td>
                            <td>${trade.pl ? formatCurrency(trade.pl) : '-'}</td>
                            <td>${trade.pl_percent ? formatPercentage(trade.pl_percent) : '-'}</td>
                            <td>${new Date(trade.timestamp).toLocaleString()}</td>
                        </tr>
                    `;
                    tbody.insertAdjacentHTML('beforeend', row);
                });
            })
            .catch(error => console.error('Error fetching trades:', error));
    }

    // Update trades immediately and every minute
    updateTrades();
    setInterval(updateTrades, 60000);
});
