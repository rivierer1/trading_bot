#!/bin/bash

# Exit on any error
set -e

echo "Starting trading bot server setup..."

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install required packages
echo "Installing required packages..."
apt install -y python3-pip python3-venv python3-dev \
    build-essential libssl-dev libffi-dev \
    nginx certbot python3-certbot-nginx \
    supervisor

# Create application directory
echo "Setting up application directory..."
mkdir -p /var/www/trading_bot
cd /var/www/trading_bot

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "Installing Python dependencies..."
pip install wheel
pip install gunicorn flask flask-socketio eventlet

# Setup Nginx configuration
echo "Configuring Nginx..."
cat > /etc/nginx/sites-available/trading_bot << 'EOF'
server {
    listen 80;
    server_name riigh.com www.riigh.com;

    location / {
        proxy_pass http://unix:/var/www/trading_bot/trading_bot.sock;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/trading_bot /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Setup Supervisor configuration
echo "Configuring Supervisor..."
cat > /etc/supervisor/conf.d/trading_bot.conf << 'EOF'
[program:trading_bot]
directory=/var/www/trading_bot
command=/var/www/trading_bot/venv/bin/gunicorn -k eventlet -w 1 -b unix:/var/www/trading_bot/trading_bot.sock web_app:app
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/trading_bot/err.log
stdout_logfile=/var/log/trading_bot/out.log
EOF

# Create log directory
mkdir -p /var/log/trading_bot
chown -R www-data:www-data /var/log/trading_bot

# Set correct permissions
echo "Setting permissions..."
chown -R www-data:www-data /var/www/trading_bot

# Restart services
echo "Restarting services..."
systemctl restart nginx
systemctl restart supervisor

# Setup SSL
echo "Setting up SSL..."
certbot --nginx -d riigh.com -d www.riigh.com --non-interactive --agree-tos --email admin@riigh.com

echo "Installation complete!"
echo "Next steps:"
echo "1. Copy your trading bot code to /var/www/trading_bot"
echo "2. Install your specific Python requirements"
echo "3. Start the application with: supervisorctl restart trading_bot"
