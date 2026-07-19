FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir yfinance pandas flask flask-socketio

# Copy application
COPY unified_strategy.py config.json ./
COPY templates/ ./templates/
COPY static/ ./static/

# Create data directory
RUN mkdir -p /data

# Set environment defaults
ENV DB_PATH=/data/trading_data.db
ENV CONFIG_PATH=/app/config.json

# Run the trader
CMD ["python3", "-u", "/app/unified_strategy.py"]