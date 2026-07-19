# AI Stock Trading Bot Dashboard

## Overview

This project provides a real-time web dashboard for monitoring an AI-driven stock trading bot. The dashboard displays portfolio value, cash, positions, profit/loss, trade history, and an equity curve. It features:

- Real-time updates via WebSocket (Flask-SocketIO)
- Secure access with HTTP Basic Auth (configurable via environment variables)
- Login attempt rate limiting to prevent brute-force attacks
- Health endpoint for monitoring
- Interactive configuration UI to adjust risk parameters, position limits, stop loss, take profit, and monitored symbols
- Trade filtering and CSV export
- Responsive design using Tailwind CSS (mobile-friendly)

## Requirements

- Python 3.8+
- pip packages: Flask, Flask-SocketIO, python-socketio, python-engineio, simple-websocket, wsproto, h11, bidict, blinker, itsdangerous, MarkupSafe, Werkzeug, etc.
- The trading bot must be writing to the SQLite database at `/root/ai_stock_trader/trading_data.db`

## Installation

1. Ensure you are in the project directory:
   ```bash
   cd /root/ai_stock_trader
   ```

2. (Optional) Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
   If you don't have a requirements.txt, you can install the packages manually:
   ```bash
   pip install flask flask-socketio
   ```

## Configuration

### Database
The dashboard expects a SQLite database file at `/root/ai_stock_trader/trading_data.db` with the following tables:
- `trades`
- `portfolio`
- `equity_history`

These are created automatically by the dashboard on first run if they don't exist.

### Authentication
By default, the dashboard uses HTTP Basic Auth with:
- Username: `admin`
- Password: `password`

You can change these by setting environment variables before starting the server:
```bash
export DASHBOARD_USER=your_username
export DASHBOARD_PASS=your_password
```
Alternatively, you can edit the `web_dashboard.py` file and change the `USERNAME` and `PASSWORD` variables.

### Configurable Trading Parameters
The dashboard allows you to adjust the following parameters via the Config modal (accessible via the gear icon):
- Risk per trade (%)
- Maximum number of concurrent positions
- Stop loss (%)
- Take profit (%)
- List of symbols to monitor (comma-separated, e.g., AAPL,MSFT,GOOGL)

These settings are saved to `/root/ai_stock_trader/config.json` and are loaded on startup.

## Running the Dashboard

### Foreground (for testing)
```bash
source venv/bin/activate   python web_dashboard.py
```
You should see output like:
```
Starting web dashboard on http://0.0.0.0:8084
 * Serving Flask app 'web_dashboard'
 * Debug mode: off
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8084
 * Running on http://<your-vps-ip>:8084
 Press CTRL+C to quit
```

### Background (using nohup or systemd)

#### Using nohup (simple)
```bash
nohup venv/bin/python web_dashboard.py > dashboard.log 2>&1 &
```
To stop it later, find the PID and kill it:
```bash
ps aux | grep web_dashboard.py
kill <PID>
```

#### Using systemd (recommended for production)
Create a service file at `/etc/systemd/system/stock-dashboard.service`:
```ini
[Unit]
Description=AI Stock Trading Bot Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/ai_stock_trader
Environment=DASHBOARD_USER=admin DASHBOARD_PASS=password
ExecStart=/root/ai_stock_trader/venv/bin/python web_dashboard.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then enable and start:
```bash
systemctl daemon-reload
systemctl enable stock-dashboard.service
systemctl start stock-dashboard.service
```
Check status:
```bash
systemctl status stock-dashboard.service
```

## API Endpoints

All endpoints (except `/health`) require HTTP Basic Auth credentials.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the main dashboard HTML page |
| `/api/status` | GET` | GET | Returns current portfolio and recent trades |
| `/api/equity` | GET | Returns equity history for charting |
| `/api/trades` | GET | Returns filtered trades (query params: symbol, start, end, limit) |
| `/api/export/csv` | GET | Returns CSV of trades (respects filters) |
| `/api/config` | GET | Returns current configuration |
| `/api/config` | POST | Updates configuration (JSON body) |
| `/api/decision` | GET | Returns recent decision log lines |
| `/health` | GET | Returns `{"status":"ok"}` if database is reachable |

### Example API Usage

```bash
# Get portfolio and trades
curl -u admin:password http://localhost:8084/api/status

# Get equity data for chart
curl -u admin:password http://localhost:8084/api/equity

# Get trades for symbol AAPL only
curl -u admin:password "http://localhost:8084/api/trades?symbol=AAPL"

# Export filtered trades as CSV
curl -u admin:password "http://localhost:8084/api/export/csv?symbol=MSFT&start=2026-07-01&end=2026-07-14" -o trades.csv

# Update config (example: change risk per trade to 3%)
curl -u admin:password -X POST http://localhost:8084/api/config \
  -H "Content-Type: application/json" \
  -d '{"risk_per_trade": 0.03}'

# Health check
curl http://localhost:8084/health
```

## Real-Time Updates

The dashboard uses WebSocket (via SocketIO) to receive push notifications when new trades are added to the database. Upon receiving a notification, the client automatically refreshes the portfolio, equity chart, and trade tables via the existing HTTP APIs. This eliminates the need for polling and provides near-instant updates.

## Login Rate Limiting

To prevent brute-force attacks, the server tracks failed login attempts per IP address. After 5 failed attempts within 60 seconds, further attempts from that IP will return a `429 Too Many Requests` response until the window expires.

## File Structure

- `web_dashboard.py` – Main Flask application with SocketIO, authentication, rate limiting, health check, and API routes.
- `templates/dashboard.html` – The single-page web interface (Tailwind CSS, Chart.js, SocketIO client).
- `config.json` – (Optional) Stores user-modified configuration parameters.
- `trading_data.db` – SQLite database populated by the trading bot.
- `README.md` – This file.

## Customization

### Change Port
Edit the `socketio.run(...)` line in `web_dashboard.py` to change the port (e.g., `port=8080`).

### Disable Debug Mode in Production
The server runs with `debug=False`. For production, consider using a proper WSGI server like Gunicorn with SocketIO workers, but for simplicity, the built-in server with `allow_unsafe_werkzeug=True` is acceptable for low-to-moderate traffic.

### Adjust Rate Limiting
Modify `MAX_ATTEMPTS` and `BLOCK_TIME` constants in `web_dashboard.py` to change the login attempt thresholds.

## Troubleshooting

- **Cannot connect**: Ensure the firewall allows traffic on port 8084 (or your configured port). Use `sudo ufw allow 8084/tcp` if using UFW.
- **Database errors**: Verify that the trading bot has write permissions to `/root/ai_stock_trader/trading_data.db` and that the directory exists.
- **No data showing**: Check that the trading bot is actively inserting rows into the `trades` and `portfolio` tables.
- **Login fails**: Confirm you are using the correct credentials (case-sensitive). Check environment variables if you changed them.
- **WebSocket not updating**: Ensure the client can connect to the server via WebSocket (port 8084). Browser console may show connection errors if blocked by firewall or CORS.

## License

This project is provided as-is for educational and informational purposes. Use at your own risk. Not financial advice.

---

*Happy trading!*